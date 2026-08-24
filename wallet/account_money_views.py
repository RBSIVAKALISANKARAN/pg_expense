from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Account, Allocation, AllocationType, MoneyLocation, MoneyPool, Transaction, TransactionType
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
    """Normalize an unambiguous stale owner/location pool context.

    A single pool for an allocation can safely be moved to the current account
    context.  When several owner pools exist, they may represent legitimate
    ownership splits, so they must not be merged merely because a deposit is
    being made by the default owner.
    """
    pools = list(
        MoneyPool.objects.filter(account=account, allocation_type=allocation_type)
        .select_for_update()
    )
    if not pools:
        return

    target_location_id = location.id
    target_owner_id = owner.id
    canonical = next(
        (pool for pool in pools if pool.location_id == target_location_id and pool.owner_id == target_owner_id),
        None,
    )

    if len(pools) == 1 and canonical is None:
        pool = pools[0]
        pool.owner_id = target_owner_id
        pool.location_id = target_location_id
        pool.save(update_fields=['owner', 'location', 'updated_at'])


def _repair_legacy_pool_balances(account, owner, location):
    """Repair old/demo wallet rows before a new money operation.

    Older data can contain a positive account total while both allocation rows
    and money pools are still zero.  That balance predates the allocation/pool
    ledger and must be treated as spendable money; otherwise the next deposit
    would make the account total diverge from its allocation ledger and the
    reconciliation guard would correctly reject the transaction.

    When the money-pool ledger already reconciles to the account total, derive
    allocation balances from the pool aggregates.  This preserves legitimate
    owner splits instead of collapsing them into the default owner.
    """
    allocation_total = account.allocations.aggregate(total=Sum('balance'))['total'] or Decimal('0')
    pool_total = account.money_pools.aggregate(total=Sum('current_amount'))['total'] or Decimal('0')

    # Legacy account-only balance: no allocation/pool information exists, so
    # the historical balance is unambiguously spendable.  Restrict this repair
    # to the three wallets that support the Savings/Spendable model.
    if (
        account.money_location_id == location.id
        and location.name in STANDARD_ALLOCATION_LOCATIONS
        and account.total_balance > 0
        and allocation_total == 0
        and pool_total == 0
    ):
        spendable = Allocation.objects.select_for_update().get(
            account=account, type=AllocationType.SPENDABLE
        )
        spendable_pool = MoneyPool.objects.filter(
            account=account,
            allocation_type=AllocationType.SPENDABLE,
        ).select_for_update().first()
        if spendable_pool is None:
            spendable_pool = MoneyPool.objects.create(
                account=account,
                owner=owner,
                location=location,
                allocation_type=AllocationType.SPENDABLE,
                current_amount=Decimal('0'),
            )
        elif spendable_pool.owner_id != owner.id or spendable_pool.location_id != location.id:
            # If there is exactly one legacy spendable pool, its context is
            # unambiguous and can be normalized before restoring its balance.
            existing_pools = MoneyPool.objects.filter(
                account=account,
                allocation_type=AllocationType.SPENDABLE,
            )
            if existing_pools.count() == 1:
                spendable_pool.owner_id = owner.id
                spendable_pool.location_id = location.id
                spendable_pool.save(update_fields=['owner', 'location', 'updated_at'])
        spendable.balance = account.total_balance
        spendable.save(update_fields=['balance', 'updated_at'])
        spendable_pool.current_amount = account.total_balance
        spendable_pool.save(update_fields=['current_amount', 'updated_at'])
        return

    if account.total_balance != pool_total:
        return

    for allocation_type in AllocationType.values:
        allocation = Allocation.objects.select_for_update().get(
            account=account, type=allocation_type
        )
        pool_allocation_total = account.money_pools.filter(
            allocation_type=allocation_type
        ).aggregate(total=Sum('current_amount'))['total'] or Decimal('0')

        if allocation.balance != pool_allocation_total:
            allocation.balance = pool_allocation_total
            allocation.save(update_fields=['balance', 'updated_at'])


def _prepare_account_money_context(account, owner, location):
    _ensure_allocations(account)
    for allocation_type in AllocationType.values:
        _repair_legacy_pool_context(account, owner, location, allocation_type)
    _sync_account_pools(account, owner, location)
    _repair_legacy_pool_balances(account, owner, location)


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
