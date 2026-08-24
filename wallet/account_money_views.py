from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Account, Allocation, AllocationType, Transaction, TransactionType
from .serializers import AccountSerializer, AllocationTransferSerializer, DepositSerializer
from .views import (
    _account_context,
    _apply_money_pool_delta,
    _assert_account_reconciles,
    _check_pool_funds,
    _ensure_allocations,
    _sync_account_pools,
)


@api_view(['POST'])
def deposit_funds_fixed(request, id):
    """Deposit money into a wallet and keep allocation/pool totals identical."""
    serializer = DepositSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data['amount']
    savings_amount = serializer.validated_data.get('allocate_to_savings', Decimal('0'))
    if savings_amount > amount:
        return Response(
            {'detail': 'Savings allocation cannot exceed deposit amount.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        spendable = Allocation.objects.select_for_update().get(
            account=account, type=AllocationType.SPENDABLE
        )
        savings = Allocation.objects.select_for_update().get(
            account=account, type=AllocationType.SAVINGS
        )
        owner, location = _account_context(
            account,
            serializer.validated_data.get('owner'),
            serializer.validated_data.get('money_location'),
        )
        _sync_account_pools(account, owner, location)

        # Use concrete Decimal values rather than F() expressions. This keeps
        # the allocation, account and money-pool reconciliation deterministic
        # for browser/API requests that immediately read the updated balance.
        spendable_amount = amount - savings_amount
        account.total_balance = account.total_balance + amount
        spendable.balance = spendable.balance + spendable_amount
        savings.balance = savings.balance + savings_amount
        account.save(update_fields=['total_balance', 'updated_at'])
        spendable.save(update_fields=['balance', 'updated_at'])
        savings.save(update_fields=['balance', 'updated_at'])

        spendable_pool = _apply_money_pool_delta(
            account, owner, location, spendable, spendable_amount
        )
        savings_pool = None
        if savings_amount:
            savings_pool = _apply_money_pool_delta(
                account, owner, location, savings, savings_amount
            )

        note = serializer.validated_data.get('note', '')
        if spendable_amount:
            Transaction.objects.create(
                account=account,
                owner=owner,
                money_location=location,
                allocation=spendable,
                source_pool=spendable_pool,
                type=TransactionType.DEPOSIT,
                amount=spendable_amount,
                metadata={'note': note, 'portion': 'spendable'} if savings_amount else {'note': note},
            )
        if savings_amount:
            Transaction.objects.create(
                account=account,
                owner=owner,
                money_location=location,
                allocation=savings,
                source_pool=savings_pool,
                type=TransactionType.DEPOSIT,
                amount=savings_amount,
                metadata={'note': note, 'portion': 'savings'},
            )

        _assert_account_reconciles(account)
        account.refresh_from_db()
        spendable.refresh_from_db()
        savings.refresh_from_db()

    return Response(AccountSerializer(account).data)


@api_view(['POST'])
def transfer_allocation_fixed(request, id, target_type):
    """Move money between spendable and savings without changing total balance."""
    data = request.data.copy()
    source_type = (
        AllocationType.SPENDABLE
        if target_type == AllocationType.SAVINGS
        else AllocationType.SAVINGS
    )
    data['from_type'] = source_type
    data['to_type'] = target_type

    serializer = AllocationTransferSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data['amount']

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=id)
        _ensure_allocations(account)
        source = Allocation.objects.select_for_update().get(
            account=account, type=source_type
        )
        target = Allocation.objects.select_for_update().get(
            account=account, type=target_type
        )
        owner, location = _account_context(
            account,
            serializer.validated_data.get('owner'),
            serializer.validated_data.get('money_location'),
        )
        _sync_account_pools(account, owner, location)

        if source.balance < amount:
            raise ValidationError({'detail': f'Not enough balance in {source_type} allocation.'})
        _check_pool_funds(account, owner, location, source, amount)

        source.balance = source.balance - amount
        target.balance = target.balance + amount
        source.save(update_fields=['balance', 'updated_at'])
        target.save(update_fields=['balance', 'updated_at'])

        source_pool = _apply_money_pool_delta(
            account, owner, location, source, -amount
        )
        target_pool = _apply_money_pool_delta(
            account, owner, location, target, amount
        )

        Transaction.objects.create(
            account=account,
            owner=owner,
            money_location=location,
            allocation=target,
            source_pool=source_pool,
            type=TransactionType.ALLOCATION,
            amount=amount,
            metadata={'from': source_type, 'to': target_type},
        )
        _assert_account_reconciles(account)
        account.refresh_from_db()

    return Response(AccountSerializer(account).data)
