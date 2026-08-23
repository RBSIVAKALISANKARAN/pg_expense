import re
from decimal import Decimal
from time import perf_counter

from django.db import connection, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.schemas import get_schema_view
from django.http import HttpResponse
from pathlib import Path

from .models import Account, Allocation, AllocationType, QueryExecutionLog, SavedQuery, Transaction, TransactionType
from .reporting import export_account_csv, summarize_account_transactions
from .serializers import (
    AccountSerializer,
    AllocationTransferSerializer,
    CreateAccountSerializer,
    DepositSerializer,
    ExpenseSerializer,
    MoneyActionSerializer,
    TransactionSerializer,
)

# schema view (OpenAPI)
schema_view = get_schema_view(title='Expense API', description='API for the Expense app', version='1.0.0')

FORBIDDEN_SQL_PATTERNS = (
    r'\bDROP\b',
    r'\bALTER\b',
    r'\bDELETE\b',
    r'\bINSERT\b',
    r'\bUPDATE\b',
    r'\bCREATE\b',
    r'\bTRUNCATE\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
    r'\bEXEC\b',
    r'\bCOPY\b',
    r'\bVACUUM\b',
    r'\bANALYZE\b',
)
ALLOWED_SQL_PREFIXES = {'SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'VALUES'}


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def _validate_sql_for_execution(raw_sql):
    if raw_sql is None:
        raise ValueError('SQL query is required.')

    sql = raw_sql.strip()
    if not sql:
        raise ValueError('SQL query is required.')

    if sql.count(';') > 1:
        raise ValueError('Only a single SQL statement is allowed.')

    sql = sql[:-1] if sql.endswith(';') else sql
    sql = sql.strip()
    if not sql:
        raise ValueError('SQL query is required.')

    if any(re.search(pattern, sql, re.IGNORECASE) for pattern in FORBIDDEN_SQL_PATTERNS):
        raise ValueError('Only read-only SQL queries are allowed in the playground.')

    prefix = sql.split(None, 1)[0].upper() if sql else ''
    if prefix not in ALLOWED_SQL_PREFIXES:
        raise ValueError('Only SELECT, WITH, SHOW, DESCRIBE, EXPLAIN, and VALUES queries are allowed.')

    return sql


def _ensure_allocations(account):
    for allocation_type in [AllocationType.SPENDABLE, AllocationType.SAVINGS]:
        Allocation.objects.get_or_create(account=account, type=allocation_type)
    return account.allocations.all()


@api_view(['GET', 'POST'])
def account_list_create(request):
    if request.method == 'GET':
        accounts = Account.objects.all()
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data)

    serializer = CreateAccountSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    account = serializer.save()
    _ensure_allocations(account)
    return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def account_detail(request, id):
    account = get_object_or_404(Account, id=id)
    _ensure_allocations(account)
    serializer = AccountSerializer(account)
    return Response(serializer.data)


@api_view(['POST'])
def deposit_funds(request, id):
    serializer = DepositSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']
    allocate_to_savings = serializer.validated_data.get('allocate_to_savings', Decimal('0'))
    if allocate_to_savings > amount:
        return Response({'detail': 'Savings allocation cannot exceed deposit amount.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)

        # Update using F() for atomic arithmetic
        account.total_balance = F('total_balance') + amount
        if allocate_to_savings > 0:
            savings.balance = F('balance') + allocate_to_savings
            spendable.balance = F('balance') + (amount - allocate_to_savings)
        else:
            spendable.balance = F('balance') + amount

        # Save changes
        account.save(update_fields=['total_balance'])
        spendable.save(update_fields=['balance'])
        savings.save(update_fields=['balance'])

        # Refresh from db to get resolved F() values
        account.refresh_from_db()
        spendable.refresh_from_db()
        savings.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=savings if allocate_to_savings > 0 else spendable,
            type=TransactionType.DEPOSIT,
            amount=amount,
            metadata={'note': serializer.validated_data.get('note', ''), 'allocate_to_savings': str(allocate_to_savings)},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def allocate_funds(request, id):
    serializer = AllocationTransferSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']
    source_type = serializer.validated_data['from_type']
    target_type = serializer.validated_data['to_type']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        source = Allocation.objects.select_for_update().get(account=account, type=source_type)
        target = Allocation.objects.select_for_update().get(account=account, type=target_type)

        if source.balance < amount:
            return Response({'detail': f'Not enough balance in {source_type} allocation.'}, status=status.HTTP_400_BAD_REQUEST)

        source.balance = F('balance') - amount
        target.balance = F('balance') + amount
        source.save(update_fields=['balance'])
        target.save(update_fields=['balance'])
        source.refresh_from_db()
        target.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=source,
            type=TransactionType.ALLOCATION,
            amount=amount,
            metadata={'from': source_type, 'to': target_type},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def expense_create(request, id):
    serializer = ExpenseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']
    allocation_type = serializer.validated_data['allocation']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        allocation = Allocation.objects.select_for_update().get(account=account, type=allocation_type)

        if allocation.balance < amount:
            return Response({'detail': f'Insufficient funds in {allocation_type} allocation.'}, status=status.HTTP_400_BAD_REQUEST)

        allocation.balance = F('balance') - amount
        account.total_balance = F('total_balance') - amount
        allocation.save(update_fields=['balance'])
        account.save(update_fields=['total_balance'])
        allocation.refresh_from_db()
        account.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=allocation,
            type=TransactionType.EXPENSE,
            amount=amount,
            metadata={'merchant': serializer.validated_data.get('merchant', ''), 'note': serializer.validated_data.get('note', '')},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_to_savings(request, id):
    serializer = MoneyActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)

        if spendable.balance < amount:
            return Response({'detail': 'Not enough spendable funds to transfer to savings.'}, status=status.HTTP_400_BAD_REQUEST)

        spendable.balance = F('balance') - amount
        savings.balance = F('balance') + amount
        spendable.save(update_fields=['balance'])
        savings.save(update_fields=['balance'])
        spendable.refresh_from_db()
        savings.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=savings,
            type=TransactionType.TRANSFER,
            amount=amount,
            metadata={'direction': 'to_savings'},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_to_spendable(request, id):
    serializer = MoneyActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)

        if savings.balance < amount:
            return Response({'detail': 'Not enough savings funds to transfer to spendable.'}, status=status.HTTP_400_BAD_REQUEST)

        savings.balance = F('balance') - amount
        spendable.balance = F('balance') + amount
        savings.save(update_fields=['balance'])
        spendable.save(update_fields=['balance'])
        savings.refresh_from_db()
        spendable.refresh_from_db()

        Transaction.objects.create(
            account=account,
            allocation=spendable,
            type=TransactionType.TRANSFER,
            amount=amount,
            metadata={'direction': 'to_spendable'},
        )

    return Response(AccountSerializer(account).data)


@api_view(['GET'])
def transactions_list(request, id):
    account = get_object_or_404(Account, id=id)
    qs = Transaction.objects.filter(account=account).order_by('-created_at')
    serializer = TransactionSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def summary_report(request, id):
    account = get_object_or_404(Account, id=id)
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    summary = summarize_account_transactions(account, start_date, end_date)
    return Response(summary)


@api_view(['GET'])
def export_report(request, id):
    account = get_object_or_404(Account, id=id)
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    csv_data = export_account_csv(account, start_date, end_date)
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="account_{id}_transactions.csv"'
    return response


@api_view(['POST'])
def sql_execute(request):
    raw_sql = request.data.get('sql', '') if isinstance(request.data, dict) else ''
    start = perf_counter()

    try:
        sql = _validate_sql_for_execution(raw_sql)
    except ValueError as exc:
        QueryExecutionLog.objects.create(
            query=str(raw_sql),
            status='error',
            execution_time_ms=0,
            error_message=str(exc),
        )
        return Response({'status': 'error', 'message': str(exc), 'execution_time_ms': 0}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            safe_rows = [
                {col: _json_safe(value) for col, value in zip(columns, row)}
                for row in rows
            ] if columns else []

            execution_time_ms = int((perf_counter() - start) * 1000)
            QueryExecutionLog.objects.create(
                query=sql,
                status='success',
                execution_time_ms=execution_time_ms,
            )
            return Response({
                'status': 'success',
                'message': 'Query executed successfully.',
                'columns': columns,
                'rows': safe_rows,
                'row_count': len(rows),
                'execution_time_ms': execution_time_ms,
            }, status=status.HTTP_200_OK)
    except Exception as exc:
        execution_time_ms = int((perf_counter() - start) * 1000)
        QueryExecutionLog.objects.create(
            query=sql if 'sql' in locals() else str(raw_sql),
            status='error',
            execution_time_ms=execution_time_ms,
            error_message=str(exc),
        )
        return Response({
            'status': 'error',
            'message': 'Query execution failed.',
            'detail': str(exc),
            'execution_time_ms': execution_time_ms,
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def sql_history(request):
    if request.method == 'GET':
        logs = QueryExecutionLog.objects.all()[:20]
        data = [
            {
                'id': str(item.id),
                'query': item.query,
                'status': item.status,
                'execution_time_ms': item.execution_time_ms,
                'error_message': item.error_message,
                'created_at': item.created_at.isoformat(),
            }
            for item in logs
        ]
        return Response(data)

    return Response({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET', 'POST', 'DELETE'])
def sql_saved_queries(request, id=None):
    if request.method == 'GET':
        if id:
            query = get_object_or_404(SavedQuery, id=id)
            return Response({
                'id': str(query.id),
                'name': query.name,
                'description': query.description,
                'sql': query.sql,
                'created_at': query.created_at.isoformat(),
            })
        queries = SavedQuery.objects.all()[:20]
        return Response([
            {
                'id': str(query.id),
                'name': query.name,
                'description': query.description,
                'sql': query.sql,
                'created_at': query.created_at.isoformat(),
            }
            for query in queries
        ])

    if request.method == 'POST':
        name = request.data.get('name', '').strip() or 'Untitled query'
        sql = request.data.get('sql', '').strip()
        description = request.data.get('description', '').strip()
        if not sql:
            return Response({'detail': 'SQL is required.'}, status=status.HTTP_400_BAD_REQUEST)
        query = SavedQuery.objects.create(name=name, description=description, sql=sql)
        return Response({
            'id': str(query.id),
            'name': query.name,
            'description': query.description,
            'sql': query.sql,
        }, status=status.HTTP_201_CREATED)

    if request.method == 'DELETE':
        query = get_object_or_404(SavedQuery, id=id)
        query.delete()
        return Response({'detail': 'Saved query deleted.'}, status=status.HTTP_200_OK)

    return Response({'detail': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET'])
def sql_schema(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
            tables = [row[0] for row in cursor.fetchall()]

            schema = []
            for table_name in tables:
                cursor.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    [table_name],
                )
                columns = [
                    {
                        'name': column_name,
                        'type': data_type,
                        'nullable': is_nullable == 'YES',
                    }
                    for column_name, data_type, is_nullable in cursor.fetchall()
                ]
                schema.append({'name': table_name, 'columns': columns})

            return Response({'tables': schema}, status=status.HTTP_200_OK)
    except Exception as exc:
        return Response({'status': 'error', 'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# Minimal dashboard view
from django.middleware.csrf import get_token


def dashboard(request):
    # ensure CSRF cookie is set for the page so fetch POST works from browser
    get_token(request)
    return render(request, 'dashboard.html')


def sql_playground(request):
    get_token(request)
    return render(request, 'sql_playground.html')


# Serve the API_DOCS.md as a simple HTML page
def docs(request):
    docs_path = Path(__file__).resolve().parent.parent / 'API_DOCS.md'
    if not docs_path.exists():
        return HttpResponse('API documentation not found', status=404)
    text = docs_path.read_text(encoding='utf-8')
    # Basic HTML escape and preformat
    from html import escape
    body = '<html><head><meta charset="utf-8"><title>API Docs</title></head><body><pre style="white-space:pre-wrap;">' + escape(text) + '</pre></body></html>'
    return HttpResponse(body, content_type='text/html')
