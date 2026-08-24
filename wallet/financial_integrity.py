from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum

from .models import Allocation, AllocationType, MoneyPool


def _allocation_type_value(allocation_or_type):
    """Normalize an Allocation instance or a raw allocation type value."""
    if isinstance(allocation_or_type, Allocation):
        return allocation_or_type.type
    return allocation_or_type


def ensure_account_money_pool(account, owner, location, allocation_type, lock=False):
    """Return the money pool belonging to this exact account context.

    Account is part of the identity. Two accounts may legitimately use the same
    owner and money location, but their balances must never share a pool.
    """
    allocation_type = _allocation_type_value(allocation_type)
    if account is None or owner is None or location is None or allocation_type is None:
        return None

    qs = MoneyPool.objects.filter(
        account=account,
        owner=owner,
        location=location,
        allocation_type=allocation_type,
    )
    pool = qs.first()
    if pool is None:
        try:
            with transaction.atomic():
                pool = MoneyPool.objects.create(
                    account=account,
                    owner=owner,
                    location=location,
                    allocation_type=allocation_type,
                    current_amount=Decimal('0'),
                )
        except IntegrityError:
            pool = qs.get()

    if lock:
        return MoneyPool.objects.select_for_update().get(pk=pool.pk)
    return pool


def sync_account_pools_with_legacy_repair(account, owner, location):
    """Synchronize an account's canonical pools and repair old account-only data.

    Older versions of the application could persist ``Account.total_balance``
    without creating matching Allocation/MoneyPool balances. A subsequent
    deposit must not add only the new amount to zero-valued buckets and then
    fail reconciliation. When the account has a positive balance but both
    allocations still total zero, that legacy balance belongs to spendable
    money by definition; restore it before the deposit is applied.
    """
    for allocation_type in (AllocationType.SPENDABLE, AllocationType.SAVINGS):
        Allocation.objects.get_or_create(account=account, type=allocation_type)

    spendable = Allocation.objects.get(account=account, type=AllocationType.SPENDABLE)
    savings = Allocation.objects.get(account=account, type=AllocationType.SAVINGS)
    allocation_total = account.allocations.aggregate(total=Sum('balance'))['total'] or Decimal('0')

    if account.total_balance > 0 and allocation_total == 0:
        spendable.balance = account.total_balance
        spendable.save(update_fields=['balance', 'updated_at'])
        savings.balance = Decimal('0')
        savings.save(update_fields=['balance', 'updated_at'])

    spendable_pool = ensure_account_money_pool(
        account, owner, location, AllocationType.SPENDABLE,
    )
    savings_pool = ensure_account_money_pool(
        account, owner, location, AllocationType.SAVINGS,
    )

    if spendable_pool.current_amount == 0 and spendable.balance != 0:
        spendable_pool.current_amount = spendable.balance
        spendable_pool.save(update_fields=['current_amount', 'updated_at'])
    if savings_pool.current_amount == 0 and savings.balance != 0:
        savings_pool.current_amount = savings.balance
        savings_pool.save(update_fields=['current_amount', 'updated_at'])

    return spendable_pool, savings_pool
