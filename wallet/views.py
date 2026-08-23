import re
from decimal import Decimal
from time import perf_counter

from django.db import connection, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.schemas import get_schema_view
from django.http import HttpResponse
from pathlib import Path

from .models import (
    Account,
    Allocation,
    AllocationType,
    Category,
    FoodProfile,
    Item,
    MoneyLocation,
    MoneyPool,
    Owner,
    QueryExecutionLog,
    SavedQuery,
    SubCategory,
    Transaction,
    TransactionType,
)
from .reporting import export_account_csv, summarize_account_transactions
from .serializers import (
    AccountSerializer,
    AllocationTransferSerializer,
    CategorySerializer,
    CreateAccountSerializer,
    DepositSerializer,
    ExpenseSerializer,
    FoodProfileSerializer,
    ItemSerializer,
    MoneyActionSerializer,
    SubCategorySerializer,
    TransactionSerializer,
    TransferSerializer,
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


def _default_owner_and_location():
    _ensure_family_defaults()
    owner = Owner.objects.filter(name='Me').first() or Owner.objects.create(name='Me')
    location = MoneyLocation.objects.filter(name='TMB Bank').first() or MoneyLocation.objects.create(name='TMB Bank')
    return owner, location


def _ensure_family_defaults():
    for owner_name in ['Me', 'Appa', 'Amma']:
        Owner.objects.get_or_create(name=owner_name, defaults={'active': True})

    for location_name, location_type in [('TMB Bank', 'bank'), ('Appa Cash', 'cash'), ('Amma Cash', 'cash')]:
        MoneyLocation.objects.get_or_create(
            name=location_name,
            defaults={'location_type': location_type, 'active': True},
        )


def _allocation_type_value(allocation_or_type):
    if isinstance(allocation_or_type, Allocation):
        return allocation_or_type.type
    return allocation_or_type


def _ensure_money_pool(owner, location, allocation_or_type):
    allocation_type = _allocation_type_value(allocation_or_type)
    if owner is None or location is None or allocation_type is None:
        return None
    pool, _ = MoneyPool.objects.get_or_create(
        owner=owner,
        location=location,
        allocation_type=allocation_type,
        defaults={'current_amount': Decimal('0')},
    )
    return pool


def _apply_money_pool_delta(owner, location, allocation_or_type, delta):
    allocation_type = _allocation_type_value(allocation_or_type)
    if owner is None or location is None or allocation_type is None:
        return None
    pool = _ensure_money_pool(owner, location, allocation_type)
    if pool is None:
        return None

    pool.refresh_from_db()
    if pool.current_amount + delta < 0:
        raise ValidationError('Money pool balance cannot go below zero.')

    if delta == Decimal('0'):
        return pool

    pool.current_amount = F('current_amount') + delta
    pool.save(update_fields=['current_amount'])
    pool.refresh_from_db()
    return pool


def _check_pool_funds(owner, location, allocation_or_type, amount):
    allocation_type = _allocation_type_value(allocation_or_type)
    if owner is None or location is None or allocation_type is None:
        return
    pool = _ensure_money_pool(owner, location, allocation_type)
    if pool is None:
        return
    pool.refresh_from_db()
    if pool.current_amount < amount:
        raise ValidationError('Insufficient funds in this specific owner\'s money pool.')


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

        default_owner, default_location = _default_owner_and_location()
        owner = serializer.validated_data.get('owner') or default_owner
        money_location = serializer.validated_data.get('money_location') or default_location

        account.total_balance = F('total_balance') + amount
        if allocate_to_savings > 0:
            savings.balance = F('balance') + allocate_to_savings
            spendable.balance = F('balance') + (amount - allocate_to_savings)
        else:
            spendable.balance = F('balance') + amount

        account.save(update_fields=['total_balance'])
        spendable.save(update_fields=['balance'])
        savings.save(update_fields=['balance'])

        account.refresh_from_db()
        spendable.refresh_from_db()
        savings.refresh_from_db()

        source_allocation = savings if allocate_to_savings > 0 else spendable
        spendable_pool = _apply_money_pool_delta(owner, money_location, spendable, Decimal(str(amount - allocate_to_savings)))
        savings_pool = None
        if allocate_to_savings > 0:
            savings_pool = _apply_money_pool_delta(owner, money_location, savings, Decimal(str(allocate_to_savings)))

        note = serializer.validated_data.get('note', '')
        if allocate_to_savings > 0:
            spendable_amount = amount - allocate_to_savings
            Transaction.objects.create(
                account=account,
                owner=owner,
                money_location=money_location,
                allocation=spendable,
                source_pool=spendable_pool,
                type=TransactionType.DEPOSIT,
                amount=spendable_amount,
                metadata={'note': note, 'allocate_to_savings': str(allocate_to_savings), 'portion': 'spendable'},
            )
            Transaction.objects.create(
                account=account,
                owner=owner,
                money_location=money_location,
                allocation=savings,
                source_pool=savings_pool,
                type=TransactionType.DEPOSIT,
                amount=allocate_to_savings,
                metadata={'note': note, 'allocate_to_savings': str(allocate_to_savings), 'portion': 'savings'},
            )
        else:
            Transaction.objects.create(
                account=account,
                owner=owner,
                money_location=money_location,
                allocation=source_allocation,
                source_pool=spendable_pool,
                type=TransactionType.DEPOSIT,
                amount=amount,
                metadata={'note': note, 'allocate_to_savings': str(allocate_to_savings)},
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

        default_owner, default_location = _default_owner_and_location()
        owner = serializer.validated_data.get('owner') or default_owner
        money_location = serializer.validated_data.get('money_location') or default_location

        if source.balance < amount:
            return Response({'detail': f'Not enough balance in {source_type} allocation.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _check_pool_funds(owner, money_location, source, amount)
        except ValidationError as exc:
            return Response({'detail': str(exc.detail[0]) if isinstance(exc.detail, list) else str(exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        source.balance = F('balance') - amount
        target.balance = F('balance') + amount
        source.save(update_fields=['balance'])
        target.save(update_fields=['balance'])
        source.refresh_from_db()
        target.refresh_from_db()

        source_pool = _apply_money_pool_delta(owner, money_location, source, -amount)
        _apply_money_pool_delta(owner, money_location, target, amount)

        Transaction.objects.create(
            account=account,
            owner=owner,
            money_location=money_location,
            allocation=source,
            source_pool=source_pool,
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

        default_owner, default_location = _default_owner_and_location()
        owner = serializer.validated_data.get('owner') or default_owner
        money_location = serializer.validated_data.get('money_location') or default_location

        if allocation.balance < amount:
            return Response({'detail': f'Insufficient funds in {allocation_type} allocation.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _check_pool_funds(owner, money_location, allocation, amount)
        except ValidationError as exc:
            return Response({'detail': str(exc.detail[0]) if isinstance(exc.detail, list) else str(exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        allocation.balance = F('balance') - amount
        account.total_balance = F('total_balance') - amount
        allocation.save(update_fields=['balance'])
        account.save(update_fields=['total_balance'])
        allocation.refresh_from_db()
        account.refresh_from_db()

        source_pool = _apply_money_pool_delta(owner, money_location, allocation, -amount)

        Transaction.objects.create(
            account=account,
            owner=owner,
            money_location=money_location,
            allocation=allocation,
            source_pool=source_pool,
            meal=serializer.validated_data.get('meal'),
            type=TransactionType.EXPENSE,
            amount=amount,
            metadata={'merchant': serializer.validated_data.get('merchant', ''), 'note': serializer.validated_data.get('note', '')},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_to_savings(request, id):
    serializer = TransferSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)

        default_owner, default_location = _default_owner_and_location()
        owner = serializer.validated_data.get('owner') or default_owner
        money_location = serializer.validated_data.get('money_location') or default_location

        if spendable.balance < amount:
            return Response({'detail': 'Not enough spendable funds to transfer to savings.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _check_pool_funds(owner, money_location, spendable, amount)
        except ValidationError as exc:
            return Response({'detail': str(exc.detail[0]) if isinstance(exc.detail, list) else str(exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        spendable.balance = F('balance') - amount
        savings.balance = F('balance') + amount
        spendable.save(update_fields=['balance'])
        savings.save(update_fields=['balance'])
        spendable.refresh_from_db()
        savings.refresh_from_db()

        source_pool = _apply_money_pool_delta(owner, money_location, spendable, -amount)
        _apply_money_pool_delta(owner, money_location, savings, amount)

        Transaction.objects.create(
            account=account,
            owner=owner,
            money_location=money_location,
            allocation=savings,
            source_pool=source_pool,
            type=TransactionType.TRANSFER,
            amount=amount,
            metadata={'direction': 'to_savings'},
        )

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_to_spendable(request, id):
    serializer = TransferSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)

        default_owner, default_location = _default_owner_and_location()
        owner = serializer.validated_data.get('owner') or default_owner
        money_location = serializer.validated_data.get('money_location') or default_location

        if savings.balance < amount:
            return Response({'detail': 'Not enough savings funds to transfer to spendable.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _check_pool_funds(owner, money_location, savings, amount)
        except ValidationError as exc:
            return Response({'detail': str(exc.detail[0]) if isinstance(exc.detail, list) else str(exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        savings.balance = F('balance') - amount
        spendable.balance = F('balance') + amount
        savings.save(update_fields=['balance'])
        spendable.save(update_fields=['balance'])
        savings.refresh_from_db()
        spendable.refresh_from_db()

        source_pool = _apply_money_pool_delta(owner, money_location, savings, -amount)
        _apply_money_pool_delta(owner, money_location, spendable, amount)

        Transaction.objects.create(
            account=account,
            owner=owner,
            money_location=money_location,
            allocation=spendable,
            source_pool=source_pool,
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


@api_view(['GET', 'POST'])
def categories_list_create(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        return Response(CategorySerializer(categories, many=True).data)

    serializer = CategorySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    category = serializer.save()
    return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def subcategories_list_create(request):
    if request.method == 'GET':
        subcategories = SubCategory.objects.select_related('category')
        return Response(SubCategorySerializer(subcategories, many=True).data)

    category_id = request.data.get('category')
    name = (request.data.get('name') or '').strip()
    description = request.data.get('description') or ''

    if not category_id:
        return Response({'detail': 'Category is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not name:
        return Response({'detail': 'Subcategory name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    category = get_object_or_404(Category, id=category_id)
    subcategory = SubCategory.objects.create(category=category, name=name, description=description)
    return Response(SubCategorySerializer(subcategory).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def items_list_create(request):
    if request.method == 'GET':
        items = Item.objects.select_related('category', 'subcategory')
        return Response(ItemSerializer(items, many=True).data)

    name = (request.data.get('name') or '').strip()
    category_id = request.data.get('category')
    subcategory_id = request.data.get('subcategory')
    description = request.data.get('description') or ''
    is_custom = bool(request.data.get('is_custom'))
    food_group = (request.data.get('food_group') or '').strip() or None
    health_classification = (request.data.get('health_classification') or '').strip() or None
    sugary = (request.data.get('sugary') or '').strip() or None

    if not name:
        return Response({'detail': 'Item name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not category_id:
        return Response({'detail': 'Category is required.'}, status=status.HTTP_400_BAD_REQUEST)

    category = get_object_or_404(Category, id=category_id)
    subcategory = None
    if subcategory_id:
        subcategory = get_object_or_404(SubCategory, id=subcategory_id)
        if subcategory.category_id != category.id:
            return Response({'detail': 'Subcategory does not belong to the selected category.'}, status=status.HTTP_400_BAD_REQUEST)

    item = Item.objects.create(category=category, subcategory=subcategory, name=name, description=description, is_custom=is_custom)

    if any(value for value in [food_group, health_classification, sugary]):
        FoodProfile.objects.update_or_create(
            item=item,
            defaults={
                'food_group': food_group or 'other',
                'health_classification': health_classification or 'unknown',
                'sugary': sugary or 'unknown',
            },
        )

    return Response(ItemSerializer(item).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def food_profiles(request):
    if request.method == 'GET':
        profiles = FoodProfile.objects.select_related('item', 'item__category')
        return Response(FoodProfileSerializer(profiles, many=True).data)

    item_id = request.data.get('item')
    if not item_id:
        return Response({'detail': 'Item is required.'}, status=status.HTTP_400_BAD_REQUEST)

    item = get_object_or_404(Item, id=item_id)
    serializer = FoodProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    profile, _ = FoodProfile.objects.update_or_create(
        item=item,
        defaults={
            'food_group': serializer.validated_data.get('food_group', 'other'),
            'health_classification': serializer.validated_data.get('health_classification', 'unknown'),
            'sugary': serializer.validated_data.get('sugary', 'unknown'),
        },
    )
    return Response(FoodProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def owners_list(request):
    _ensure_family_defaults()
    owners = Owner.objects.filter(active=True).order_by('name')
    return Response([
        {'id': str(owner.id), 'name': owner.name, 'active': owner.active}
        for owner in owners
    ])


@api_view(['GET'])
def money_locations_list(request):
    _ensure_family_defaults()
    locations = MoneyLocation.objects.filter(active=True).order_by('name')
    return Response([
        {'id': str(location.id), 'name': location.name, 'location_type': location.location_type, 'active': location.active}
        for location in locations
    ])


@api_view(['GET'])
def money_pools_list(request):
    pools = MoneyPool.objects.select_related('owner', 'location').order_by('owner__name', 'location__name', 'allocation_type')
    return Response([
        {
            'id': str(pool.id),
            'owner': {'id': str(pool.owner_id), 'name': pool.owner.name},
            'location': {'id': str(pool.location_id), 'name': pool.location.name},
            'allocation_type': pool.allocation_type,
            'current_amount': str(pool.current_amount),
        }
        for pool in pools
    ])


@api_view(['GET'])
def app_settings(request):
    settings_payload = {
        'app_name': 'Expense Tracking Savings Spendable',
        'currency_default': 'INR',
        'timezone': 'Asia/Kolkata',
        'default_allocation': 'spendable',
        'default_owner': 'Me',
        'default_money_location': 'TMB Bank',
        'features': ['wallet', 'expenses', 'sql_playground', 'saved_queries', 'history', 'category_tracking', 'family_money'],
    }
    return Response(settings_payload)


def settings_page(request):
    return render(request, 'settings.html', {
        'app_name': 'Expense Tracking Savings Spendable',
        'currency_default': 'INR',
        'timezone': 'Asia/Kolkata',
        'default_allocation': 'spendable',
    })


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


# Minimal dashboard and page views
from django.middleware.csrf import get_token


def dashboard(request):
    get_token(request)
    return render(request, 'dashboard.html')


def accounts_page(request):
    get_token(request)
    return render(request, 'accounts.html')


def transactions_page(request):
    get_token(request)
    return render(request, 'transactions.html')


def categories_page(request):
    get_token(request)
    return render(request, 'categories.html')


def report_page(request):
    get_token(request)
    return render(request, 'reports.html')


def sql_playground(request):
    get_token(request)
    return render(request, 'sql_playground.html')


def database_structure_page(request):
    get_token(request)
    return render(request, 'database_structure.html', {
        'tables': [
            {
                'name': 'wallet_account',
                'description': 'Top-level money container for a wallet/account.',
                'columns': ['id', 'name', 'total_balance', 'currency', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_allocation',
                'description': 'Spendable and savings split per account.',
                'columns': ['id', 'account_id', 'type', 'balance', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_transaction',
                'description': 'All money movements, expenses, and transfers.',
                'columns': ['id', 'account_id', 'owner_id', 'money_location_id', 'allocation_id', 'source_pool_id', 'category_id', 'subcategory_id', 'item_id', 'meal', 'type', 'amount', 'metadata', 'created_at', 'related_tx_id'],
            },
            {
                'name': 'wallet_category',
                'description': 'Primary expense category bucket.',
                'columns': ['id', 'name', 'description', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_subcategory',
                'description': 'Secondary category split within a category.',
                'columns': ['id', 'category_id', 'name', 'description', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_item',
                'description': 'Specific item or manual entry used in transactions.',
                'columns': ['id', 'category_id', 'subcategory_id', 'name', 'description', 'is_custom', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_owner',
                'description': 'Who owns the money pool or transaction context.',
                'columns': ['id', 'name', 'active', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_moneylocation',
                'description': 'Where the money is kept such as TMB Bank or Appa Cash.',
                'columns': ['id', 'name', 'location_type', 'active', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_moneypool',
                'description': 'Owner + location + allocation totals in one combined bucket.',
                'columns': ['id', 'owner_id', 'location_id', 'allocation_id', 'current_amount', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_savedquery',
                'description': 'Saved SQL queries created by the user.',
                'columns': ['id', 'name', 'description', 'sql', 'created_at', 'updated_at'],
            },
            {
                'name': 'wallet_queryexecutionlog',
                'description': 'History of executed read-only playground queries.',
                'columns': ['id', 'query', 'status', 'execution_time_ms', 'error_message', 'created_at'],
            },
        ],
        'relationships': [
            ('wallet_account', 'wallet_allocation', 'one-to-many: account -> allocations'),
            ('wallet_account', 'wallet_transaction', 'one-to-many: account -> transactions'),
            ('wallet_category', 'wallet_subcategory', 'one-to-many: category -> subcategories'),
            ('wallet_category', 'wallet_item', 'one-to-many: category -> items'),
            ('wallet_owner', 'wallet_moneylocation', 'many-to-many through money pool'),
            ('wallet_allocation', 'wallet_moneypool', 'one-to-many: allocation -> money pools'),
            ('wallet_owner', 'wallet_transaction', 'optional many-to-one: owner -> transactions'),
            ('wallet_moneylocation', 'wallet_transaction', 'optional many-to-one: location -> transactions'),
        ]
    })


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
