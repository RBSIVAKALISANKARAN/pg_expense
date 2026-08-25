import hmac
import os
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Account, Allocation, AllocationType, MoneyPool
from .views import _account_context, _assert_account_reconciles, _ensure_allocations, _ensure_money_pool


# Demo/local recovery credentials. Override these through environment variables
# before deploying anywhere beyond a private development machine.
POWER_OVERRIDE_USERNAME = os.getenv('POWER_OVERRIDE_USERNAME', '421688')
POWER_OVERRIDE_PASSWORD = os.getenv('POWER_OVERRIDE_PASSWORD', '421688')
TARGET_ACCOUNT_NAME = 'rbsankaran_acc'


def _authorized(username, password):
    return hmac.compare_digest(str(username or ''), POWER_OVERRIDE_USERNAME) and hmac.compare_digest(
        str(password or ''), POWER_OVERRIDE_PASSWORD
    )


def _set_account_balances(account, total, savings):
    """Force an account into a reconciled total/spendable/savings state."""
    _ensure_allocations(account)
    spendable = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SPENDABLE)
    savings_allocation = Allocation.objects.select_for_update().get(account=account, type=AllocationType.SAVINGS)
    owner, location = _account_context(account)

    spendable_amount = total - savings
    account.total_balance = total
    spendable.balance = spendable_amount
    savings_allocation.balance = savings
    account.save(update_fields=['total_balance', 'updated_at'])
    spendable.save(update_fields=['balance', 'updated_at'])
    savings_allocation.save(update_fields=['balance', 'updated_at'])

    # An override deliberately replaces the current pool distribution with one
    # canonical owner/location context. Historical transactions are preserved.
    for pool in MoneyPool.objects.select_for_update().filter(account=account):
        pool.current_amount = Decimal('0')
        pool.save(update_fields=['current_amount', 'updated_at'])

    spendable_pool = _ensure_money_pool(account, owner, location, spendable, lock=True)
    savings_pool = _ensure_money_pool(account, owner, location, savings_allocation, lock=True)
    spendable_pool.current_amount = spendable_amount
    savings_pool.current_amount = savings
    spendable_pool.save(update_fields=['current_amount', 'updated_at'])
    savings_pool.save(update_fields=['current_amount', 'updated_at'])

    account.refresh_from_db()
    _assert_account_reconciles(account)
    return account


@login_required
def power_override_page(request):
    account = Account.objects.filter(name=TARGET_ACCOUNT_NAME).first()
    return render(request, 'power_override.html', {'account': account})


@api_view(['POST'])
@login_required
def power_override(request):
    data = request.data if isinstance(request.data, dict) else {}
    if not _authorized(data.get('username'), data.get('password')):
        return Response({'detail': 'Power override credentials are invalid.'}, status=status.HTTP_403_FORBIDDEN)

    action = str(data.get('action', '')).strip()

    with transaction.atomic():
        if action == 'set_rbsankaran_balance':
            try:
                total = Decimal(str(data.get('total_balance', ''))).quantize(Decimal('0.01'))
                savings = Decimal(str(data.get('savings_balance', '0'))).quantize(Decimal('0.01'))
            except (InvalidOperation, ValueError):
                return Response({'detail': 'Enter valid monetary values.'}, status=status.HTTP_400_BAD_REQUEST)
            if total < 0 or savings < 0:
                return Response({'detail': 'Balances cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
            if savings > total:
                return Response({'detail': 'Savings cannot exceed total balance.'}, status=status.HTTP_400_BAD_REQUEST)

            account = Account.objects.select_for_update().filter(name=TARGET_ACCOUNT_NAME).first()
            if account is None:
                return Response({'detail': f'Account {TARGET_ACCOUNT_NAME} was not found.'}, status=status.HTTP_404_NOT_FOUND)
            _set_account_balances(account, total, savings)
            return Response({
                'detail': f'{TARGET_ACCOUNT_NAME} balance overridden successfully.',
                'account': account.name,
                'total_balance': str(account.total_balance),
                'spendable_balance': str(total - savings),
                'savings_balance': str(savings),
            })

        if action == 'reset_all_balances':
            accounts = list(Account.objects.select_for_update().all())
            for account in accounts:
                _ensure_allocations(account)
                account.total_balance = Decimal('0')
                account.save(update_fields=['total_balance', 'updated_at'])
                Allocation.objects.filter(account=account).update(balance=Decimal('0'))
                MoneyPool.objects.filter(account=account).update(current_amount=Decimal('0'))
                account.refresh_from_db()
                _assert_account_reconciles(account)
            return Response({'detail': f'All {len(accounts)} wallet balances were reset to ₹0.00.'})

    return Response({'detail': 'Unknown power override action.'}, status=status.HTTP_400_BAD_REQUEST)
