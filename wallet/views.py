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
    location = account_location = MoneyLocation.objects.filter(name='rbsankaran_acc').first()
    if location is None:
        location = MoneyLocation.objects.create(name='rbsankaran_acc', location_type='bank', active=True)
    return owner, location


def _account_context(account, requested_owner=None, requested_location=None):
    """Return a valid owner/location context for an account action.

    The selected money location must match the account's assigned location.
    Owners are independent of the account and default to the canonical active owner.
    """
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
        ('rbsankaran_acc', 'bank'),
        ('Appa Cash', 'cash'),
        ('Amma Cash', 'cash'),
        ('Change Cash', 'change_cash'),
        ('Travel Card', 'travel_card'),
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
    """Return the account-scoped pool without deleting unrelated account pools."""
    allocation_type = _allocation_type_value(allocation_or_type)
    if account is None or owner is None or location is None or allocation_type is None:
        return None

    pool = MoneyPool.objects.filter(
        account=account,
        owner=owner,
        location=location,
        allocation_type=allocation_type,
    ).first()
    if pool is None:
        pool = MoneyPool.objects.create(
            account=account,
            owner=owner,
            location=location,
            allocation_type=allocation_type,
            current_amount=Decimal('0'),
        )
    return MoneyPool.objects.select_for_update().get(pk=pool.pk) if lock else pool


def _sync_account_pools(account, owner, location):
    """Ensure the selected account context has one pool per canonical allocation."""
    _ensure_allocations(account)
    spendable = Allocation.objects.get(account=account, type=AllocationType.SPENDABLE)
    savings = Allocation.objects.get(account=account, type=AllocationType.SAVINGS)
    spendable_pool = _ensure_money_pool(account, owner, location, spendable)
    savings_pool = _ensure_money_pool(account, owner, location, savings)
    # Newly-created pools start at zero. For a legacy account whose only
    # account-scoped pools are missing, seed the canonical pools from the
    # allocation balances so reconciliation can proceed without forcing a
    # destructive reset of existing financial data.
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
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data)
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
        source_allocation = savings if allocate_to_savings > 0 else spendable
        spendable_pool = _apply_money_pool_delta(account, owner, money_location, spendable, amount - allocate_to_savings)
        savings_pool = None
        if allocate_to_savings > 0:
            savings_pool = _apply_money_pool_delta(account, owner, money_location, savings, allocate_to_savings)
        note = serializer.validated_data.get('note', '')
        if allocate_to_savings > 0:
            spendable_amount = amount - allocate_to_savings
            Transaction.objects.create(account=account, owner=owner, money_location=money_location, allocation=spendable, source_pool=spendable_pool, type=TransactionType.DEPOSIT, amount=spendable_amount, metadata={'note': note, 'allocate_to_savings': str(allocate_to_savings), 'portion': 'spendable'})
            Transaction.objects.create(account=account, owner=owner, money_location=money_location, allocation=savings, source_pool=savings_pool, type=TransactionType.DEPOSIT, amount=allocate_to_savings, metadata={'note': note, 'allocate_to_savings': str(allocate_to_savings), 'portion': 'savings'})
        else:
            Transaction.objects.create(account=account, owner=owner, money_location=money_location, allocation=source_allocation, source_pool=spendable_pool, type=TransactionType.DEPOSIT, amount=amount, metadata={'note': note, 'allocate_to_savings': str(allocate_to_savings)})
        _assert_account_reconciles(account)
    return Response(AccountSerializer(account).data)
