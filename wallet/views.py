import re
from decimal import Decimal
from time import perf_counter

from django.db import connection, transaction
from django.db.models import F, Sum
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
    FoodEvent,
    FoodEventItem,
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

schema_view = get_schema_view(title='Expense API', description='API for the Expense app', version='1.0.0')

FORBIDDEN_SQL_PATTERNS = (
    r'\bDROP\b', r'\bALTER\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b',
    r'\bCREATE\b', r'\bTRUNCATE\b', r'\bGRANT\b', r'\bREVOKE\b', r'\bEXEC\b',
    r'\bCOPY\b', r'\bVACUUM\b', r'\bANALYZE\b',
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
    for allocation_type in (AllocationType.SPENDABLE, AllocationType.SAVINGS):
        Allocation.objects.get_or_create(account=account, type=allocation_type)
    return account.allocations.all()


def _default_owner_and_location():
    _ensure_family_defaults()
    owner, _ = Owner.objects.get_or_create(name='Me', defaults={'active': True})
    location = MoneyLocation.objects.filter(name='rbsankaran_acc').first()
    if location is None:
        location = MoneyLocation.objects.create(name='rbsankaran_acc', location_type='bank', active=True)
    return owner, location


def _account_context(account, requested_owner=None, requested_location=None):
    default_owner, default_location = _default_owner_and_location()
    owner = requested_owner or default_owner
    location = requested_location or account.money_location or default_location
    if not owner.active:
        raise ValidationError('The selected owner is inactive.')
    if not location.active:
        raise ValidationError('The selected money location is inactive.')
    if account.money_location_id and account.money_location_id != location.id:
        raise ValidationError('The supplied money location does not belong to this account.')
    if not account.money_location_id:
        account.money_location = location
        account.save(update_fields=['money_location', 'updated_at'])
    return owner, location


def _ensure_family_defaults():
    for owner_name in ['Me', 'Appa', 'Amma']:
        Owner.objects.get_or_create(name=owner_name, defaults={'active': True})
    for location_name, location_type in [
        ('rbsankaran_acc', 'bank'), ('Appa Cash', 'cash'), ('Amma Cash', 'cash'),
        ('Change Cash', 'change_cash'), ('Travel Card', 'travel_card'),
    ]:
        MoneyLocation.objects.get_or_create(
            name=location_name,
            defaults={'location_type': location_type, 'active': True},
        )


def _allocation_type_value(allocation_or_type):
    if isinstance(allocation_or_type, Allocation):
        return allocation_or_type.type
    return allocation_or_type


def _ensure_money_pool(account, owner, location, allocation_or_type, lock=False):
    allocation_type = _allocation_type_value(allocation_or_type)
    if account is None or owner is None or location is None or allocation_type is None:
        return None
    pool = MoneyPool.objects.filter(
        account=account, owner=owner, location=location, allocation_type=allocation_type,
    ).first()
    if pool is None:
        pool = MoneyPool.objects.create(
            account=account, owner=owner, location=location,
            allocation_type=allocation_type, current_amount=Decimal('0'),
        )
    return MoneyPool.objects.select_for_update().get(pk=pool.pk) if lock else pool


def _sync_account_pools(account, owner, location):
    _ensure_allocations(account)
    spendable = Allocation.objects.get(account=account, type=AllocationType.SPENDABLE)
    savings = Allocation.objects.get(account=account, type=AllocationType.SAVINGS)
    spendable_pool = _ensure_money_pool(account, owner, location, spendable)
    savings_pool = _ensure_money_pool(account, owner, location, savings)
    if spendable_pool.current_amount == 0 and spendable.balance != 0:
        spendable_pool.current_amount = spendable.balance
        spendable_pool.save(update_fields=['current_amount', 'updated_at'])
    if savings_pool.current_amount == 0 and savings.balance != 0:
        savings_pool.current_amount = savings.balance
        savings_pool.save(update_fields=['current_amount', 'updated_at'])
    return spendable_pool, savings_pool


def _apply_money_pool_delta(account, owner, location, allocation_or_type, delta):
    allocation_type = _allocation_type_value(allocation_or_type)
    if owner is None or location is None or allocation_type is None:
        return None
    pool = _ensure_money_pool(account, owner, location, allocation_type, lock=True)
    if pool is None:
        return None
    if pool.current_amount + delta < 0:
        raise ValidationError('Money pool balance cannot go below zero.')
    if delta == Decimal('0'):
        return pool
    pool.current_amount = F('current_amount') + delta
    pool.save(update_fields=['current_amount', 'updated_at'])
    pool.refresh_from_db()
    return pool


def _check_pool_funds(account, owner, location, allocation_or_type, amount):
    allocation_type = _allocation_type_value(allocation_or_type)
    if owner is None or location is None or allocation_type is None:
        return
    pool = _ensure_money_pool(account, owner, location, allocation_type, lock=True)
    if pool is None:
        return
    pool.refresh_from_db()
    if pool.current_amount < amount:
        raise ValidationError("Insufficient funds in this specific owner's money pool.")


def _assert_account_reconciles(account):
    allocation_total = account.allocations.aggregate(total=Sum('balance'))['total'] or Decimal('0')
    pool_total = account.money_pools.aggregate(total=Sum('current_amount'))['total'] or Decimal('0')
    if account.total_balance != allocation_total:
        raise ValidationError('Account allocation reconciliation failed; no changes were saved.')
    if account.total_balance != pool_total:
        raise ValidationError('Account money-pool reconciliation failed; no changes were saved.')


@api_view(['GET', 'POST'])
def account_list_create(request):
    if request.method == 'GET':
        accounts = Account.objects.select_related('money_location').all()
        for account in accounts:
            _ensure_allocations(account)
        return Response(AccountSerializer(accounts, many=True).data)
    serializer = CreateAccountSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        requested_location = serializer.validated_data.get('money_location')
        if requested_location is None:
            requested_location, _ = MoneyLocation.objects.get_or_create(
                name=serializer.validated_data['name'],
                defaults={'location_type': 'bank', 'active': True},
            )
        account = serializer.save(money_location=requested_location)
        _ensure_allocations(account)
        owner, location = _account_context(account)
        _sync_account_pools(account, owner, location)
    return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def account_detail(request, id):
    account = get_object_or_404(Account, id=id)
    _ensure_allocations(account)
    owner, location = _account_context(account)
    _sync_account_pools(account, owner, location)
    return Response(AccountSerializer(account).data)


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
        owner, money_location = _account_context(account, serializer.validated_data.get('owner'), serializer.validated_data.get('money_location'))
        _sync_account_pools(account, owner, money_location)
        account.total_balance = F('total_balance') + amount
        if allocate_to_savings > 0:
            savings.balance = F('balance') + allocate_to_savings
            spendable.balance = F('balance') + (amount - allocate_to_savings)
        else:
            spendable.balance = F('balance') + amount
        account.save(update_fields=['total_balance'])
        spendable.save(update_fields=['balance'])
        savings.save(update_fields=['balance'])
        account.refresh_from_db(); spendable.refresh_from_db(); savings.refresh_from_db()
        spendable_pool = _apply_money_pool_delta(account, owner, money_location, spendable, amount - allocate_to_savings)
        savings_pool = None
        if allocate_to_savings > 0:
            savings_pool = _apply_money_pool_delta(account, owner, money_location, savings, allocate_to_savings)
        note = serializer.validated_data.get('note', '')
        if allocate_to_savings > 0:
            spendable_amount = amount - allocate_to_savings
            Transaction.objects.create(account=account, owner=owner, money_location=money_location, allocation=spendable, source_pool=spendable_pool, type=TransactionType.DEPOSIT, amount=spendable_amount, metadata={'note': note, 'portion': 'spendable'})
            Transaction.objects.create(account=account, owner=owner, money_location=money_location, allocation=savings, source_pool=savings_pool, type=TransactionType.DEPOSIT, amount=allocate_to_savings, metadata={'note': note, 'portion': 'savings'})
        else:
            Transaction.objects.create(account=account, owner=owner, money_location=money_location, allocation=spendable, source_pool=spendable_pool, type=TransactionType.DEPOSIT, amount=amount, metadata={'note': note})
        _assert_account_reconciles(account)
    return Response(AccountSerializer(account).data)


# ---- Compatibility/page views -------------------------------------------------
# The demo branch split feature APIs into phase-specific modules. These small
# compatibility views preserve the original URLs used by the templates and E2E
# browser flow without duplicating the newer feature implementations.


def _page(request, template):
    from django.middleware.csrf import get_token
    get_token(request)
    return render(request, template)


def dashboard(request):
    return _page(request, 'dashboard.html')


def accounts_page(request):
    return _page(request, 'accounts.html')


def transactions_page(request):
    return _page(request, 'transactions.html')


def categories_page(request):
    return _page(request, 'categories.html')


def report_page(request):
    return _page(request, 'reports.html')


def sql_playground(request):
    return _page(request, 'sql_playground.html')


def database_structure_page(request):
    return _page(request, 'database_structure.html')


@api_view(['GET', 'POST'])
def categories_list_create(request):
    if request.method == 'GET':
        return Response(CategorySerializer(Category.objects.filter(active=True), many=True).data)
    serializer = CategorySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(CategorySerializer(serializer.save()).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def subcategories_list_create(request):
    if request.method == 'GET':
        return Response(SubCategorySerializer(SubCategory.objects.select_related('category').filter(active=True), many=True).data)
    serializer = SubCategorySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(SubCategorySerializer(serializer.save()).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def items_list_create(request):
    if request.method == 'GET':
        return Response(ItemSerializer(Item.objects.select_related('category', 'subcategory').filter(active=True), many=True).data)
    serializer = ItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(ItemSerializer(serializer.save()).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def food_profiles(request):
    if request.method == 'GET':
        return Response(FoodProfileSerializer(FoodProfile.objects.select_related('item').all(), many=True).data)
    serializer = FoodProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(FoodProfileSerializer(serializer.save()).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def owners_list(request):
    return Response([{'id': str(o.id), 'name': o.name, 'active': o.active} for o in Owner.objects.filter(active=True)])


@api_view(['GET'])
def money_locations_list(request):
    return Response([{'id': str(x.id), 'name': x.name, 'location_type': x.location_type, 'active': x.active} for x in MoneyLocation.objects.filter(active=True)])


@api_view(['GET'])
def money_pools_list(request):
    pools = MoneyPool.objects.select_related('account', 'owner', 'location').all()
    return Response([{
        'id': str(p.id), 'account': str(p.account_id) if p.account_id else None,
        'owner': str(p.owner_id) if p.owner_id else None,
        'owner_name': p.owner.name if p.owner else None,
        'location': str(p.location_id) if p.location_id else None,
        'location_name': p.location.name if p.location else None,
        'allocation_type': p.allocation_type,
        'current_amount': str(p.current_amount),
    } for p in pools])


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
        owner, location = _account_context(account, serializer.validated_data.get('owner'), serializer.validated_data.get('money_location'))
        _sync_account_pools(account, owner, location)
        if source.balance < amount:
            return Response({'detail': f'Not enough balance in {source_type} allocation.'}, status=400)
        _check_pool_funds(account, owner, location, source, amount)
        source.balance = F('balance') - amount
        target.balance = F('balance') + amount
        source.save(update_fields=['balance']); target.save(update_fields=['balance'])
        source.refresh_from_db(); target.refresh_from_db()
        source_pool = _apply_money_pool_delta(account, owner, location, source, -amount)
        _apply_money_pool_delta(account, owner, location, target, amount)
        Transaction.objects.create(account=account, owner=owner, money_location=location, allocation=target, source_pool=source_pool, type=TransactionType.ALLOCATION, amount=amount, metadata={'from': source_type, 'to': target_type})
        _assert_account_reconciles(account)
    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_to_savings(request, id):
    data = dict(request.data)
    data['from_type'] = AllocationType.SPENDABLE
    data['to_type'] = AllocationType.SAVINGS
    request._full_data = data
    return allocate_funds(request, id)


@api_view(['POST'])
def transfer_to_spendable(request, id):
    data = dict(request.data)
    data['from_type'] = AllocationType.SAVINGS
    data['to_type'] = AllocationType.SPENDABLE
    request._full_data = data
    return allocate_funds(request, id)


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
        owner, location = _account_context(account, serializer.validated_data.get('owner'), serializer.validated_data.get('money_location'))
        _sync_account_pools(account, owner, location)
        if allocation.balance < amount:
            return Response({'detail': f'Insufficient funds in {allocation_type} allocation.'}, status=400)
        _check_pool_funds(account, owner, location, allocation, amount)
        allocation.balance = F('balance') - amount
        account.total_balance = F('total_balance') - amount
        allocation.save(update_fields=['balance']); account.save(update_fields=['total_balance'])
        allocation.refresh_from_db(); account.refresh_from_db()
        source_pool = _apply_money_pool_delta(account, owner, location, allocation, -amount)
        Transaction.objects.create(
            account=account, owner=owner, money_location=location, allocation=allocation,
            source_pool=source_pool, category=serializer.validated_data.get('category'),
            subcategory=serializer.validated_data.get('subcategory'), item=serializer.validated_data.get('item'),
            variant=serializer.validated_data.get('variant', ''), meal=serializer.validated_data.get('meal'),
            type=TransactionType.EXPENSE, amount=amount,
            metadata={'merchant': serializer.validated_data.get('merchant', ''), 'note': serializer.validated_data.get('note', ''), 'custom_description': serializer.validated_data.get('custom_description', '')},
        )
        _assert_account_reconciles(account)
    return Response(AccountSerializer(account).data)


@api_view(['GET'])
def transactions_list(request, id):
    qs = Transaction.objects.filter(account_id=id).select_related('category', 'subcategory', 'item', 'owner', 'money_location', 'allocation').order_by('-occurred_at', '-created_at')
    return Response(TransactionSerializer(qs, many=True).data)


def _all_transactions(request):
    qs = Transaction.objects.select_related('account', 'category', 'subcategory', 'item', 'owner', 'money_location', 'allocation').order_by('-occurred_at', '-created_at')
    return qs


@api_view(['GET'])
def summary_report(request, id):
    account = get_object_or_404(Account, id=id)
    return Response(summarize_account_transactions(account))


@api_view(['GET'])
def export_report(request, id):
    response = export_account_csv(id)
    return response


@api_view(['GET'])
def transactions_page(request):
    return _page(request, 'transactions.html')


@api_view(['GET'])
def sql_execute(request):
    from .sql_security import sql_execute_secure
    return sql_execute_secure(request)


def docs(request):
    docs_path = Path(__file__).resolve().parent.parent / 'API_DOCS.md'
    if not docs_path.exists():
        return HttpResponse('API documentation not found', status=404)
    from html import escape
    return HttpResponse(f'<pre>{escape(docs_path.read_text(encoding="utf-8"))}</pre>')
