from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Account, Allocation, AllocationType, MoneyPool, Transaction, TransactionType
from .serializers import AccountSerializer, AllocationTransferSerializer, DepositSerializer
from .views import (
    _account_context,
    _apply_money_pool_delta,
    _assert_account_reconciles,
    _check_pool_funds,
    _ensure_allocations,
    _sync_account_pools,
)


STANDARD_ALLOCATION_LOCATIONS = {'rbsankaran_acc', 'Amma Cash', 'Appa Cash'}


def _repair_legacy_pool_context(account, owner, location, allocation_type):
    """Repair a legacy pool whose account is correct but owner/location is stale.

    Older wallet migrations changed the MoneyPool identity rules.  A standard
    wallet can therefore have one existing pool attached to the right account
    and allocation but an obsolete owner/location pair.  Reusing that single
    pool is safe and prevents _sync_account_pools from creating a second pool,
    which would make reconciliation fail after a deposit.
    """
    pools = list(
        MoneyPool.objects.filter(account=account, allocation_type=allocation_type)
        .select_for_update()
    )
    if len(pools) == 1:
        pool = pools[0]
        if pool.owner_id != owner.id or pool.location_id != location.id:
            pool.owner = owner
            pool.location = location
            pool.save(update_fields=['owner', 'location', 'updated_at'])


def _prepare_account_money_context(account, owner, location):
    _ensure_allocations(account)
    for allocation_type in AllocationType.values:
        _repair_legacy_pool_context(account, owner, location, allocation_type)
    _sync_account_pools(account, owner, location)


@api_view(['POST'])
def deposit_funds_fixed(request, id):
    """Deposit money into a wallet and keep allocation/pool totals identical."""
    serializer = DepositSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data['amount']
    savings_amount = serializer.validated_data.get('allocate_to_savings', Decimal('0'))
    if savings_amount > amount:
        return Response({'detail': 'Savings allocation cannot exceed deposit amount.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
        savings = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)
        owner, location = _account_context(account, serializer.validated_data.get('owner'), serializer.validated_data.get('money_location'))
        _prepare_account_money_context(account, owner, location)

        spendable_amount = amount - savings_amount
        account.total_balance = account.total_balance + amount
        spendable.balance = spendable.balance + spendable_amount
        savings.balance = savings.balance + savings_amount
        account.save(update_fields=['total_balance', 'updated_at'])
        spendable.save(update_fields=['balance', 'updated_at'])
        savings.save(update_fields=['balance', 'updated_at'])

        spendable_pool = _apply_money_pool_delta(account, owner, location, spendable, spendable_amount)
        savings_pool = _apply_money_pool_delta(account, owner, location, savings, savings_amount) if savings_amount else None
        note = serializer.validated_data.get('note', '')

        if spendable_amount:
            Transaction.objects.create(
                account=account, owner=owner, money_location=location, allocation=spendable,
                source_pool=spendable_pool, type=TransactionType.DEPOSIT,
                amount=spendable_amount,
                metadata={'note': note, 'portion': 'spendable'} if savings_amount else {'note': note},
            )
        if savings_amount:
            Transaction.objects.create(
                account=account, owner=owner, money_location=location, allocation=savings,
                source_pool=savings_pool, type=TransactionType.DEPOSIT, amount=savings_amount,
                metadata={'note': note, 'portion': 'savings'},
            )

        account.refresh_from_db()
        spendable.refresh_from_db()
        savings.refresh_from_db()
        _assert_account_reconciles(account)

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_allocation_fixed(request, id, target_type=None):
    """Move money between spendable and savings without changing total balance."""
    data = request.data.copy()
    if target_type is None:
        source_type = data.get('from_type')
        target_type = data.get('to_type')
        if source_type not in AllocationType.values or target_type not in AllocationType.values:
            raise ValidationError({'detail': 'from_type and to_type must be spendable or savings.'})
    else:
        source_type = AllocationType.SPENDABLE if target_type == AllocationType.SAVINGS else AllocationType.SAVINGS
        data['from_type'] = source_type
        data['to_type'] = target_type

    serializer = AllocationTransferSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data['amount']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        source = Allocation.objects.select_for_update().get(account=account, type=source_type)
        target = Allocation.objects.select_for_update().get(account=account, type=target_type)
        owner, location = _account_context(account, serializer.validated_data.get('owner'), serializer.validated_data.get('money_location'))
        _prepare_account_money_context(account, owner, location)

        if source.balance < amount:
            raise ValidationError({'detail': f'Not enough balance in {source_type} allocation.'})
        _check_pool_funds(account, owner, location, source, amount)

        source.balance = source.balance - amount
        target.balance = target.balance + amount
        source.save(update_fields=['balance', 'updated_at'])
        target.save(update_fields=['balance', 'updated_at'])

        source_pool = _apply_money_pool_delta(account, owner, location, source, -amount)
        _apply_money_pool_delta(account, owner, location, target, amount)
        Transaction.objects.create(
            account=account, owner=owner, money_location=location, allocation=target,
            source_pool=source_pool, type=TransactionType.ALLOCATION, amount=amount,
            metadata={'from': source_type, 'to': target_type},
        )
        account.refresh_from_db()
        _assert_account_reconciles(account)

    return Response(AccountSerializer(account).data)
