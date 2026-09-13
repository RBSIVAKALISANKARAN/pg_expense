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

    Creation is race-safe because the database uniqueness constraint is the
    final arbiter of pool identity. If another transaction creates the same
    pool concurrently, the losing transaction rolls back its savepoint and
    retrieves the committed row.
    """
    allocation_type = _allocation_type_value(allocation_type)
    if account is None or owner is None or location is None or allocation_type is None:
        return None

    lookup = {
        'account': account,
        'owner': owner,
        'location': location,
        'allocation_type': allocation_type,
    }

    if lock:
        # A select_for_update() on an existing row gives callers a stable row
        # lock before they mutate the pool. If the row does not exist yet,
        # creation below is still protected by the database unique constraint.
        pool = MoneyPool.objects.select_for_update().filter(**lookup).first()
        if pool is not None:
            return pool

    else:
        pool = MoneyPool.objects.filter(**lookup).first()
        if pool is not None:
            return pool

    try:
        with transaction.atomic():
            pool = MoneyPool.objects.create(
                **lookup,
                current_amount=Decimal('0'),
            )
    except IntegrityError:
        # The INSERT may lose a concurrent uniqueness race. The savepoint
        # above is rolled back, making it safe to issue the SELECT afterwards.
        pool = MoneyPool.objects.filter(**lookup).first()
        if pool is None:
            # The concurrent transaction may not have committed yet. Let the
            # database/application surface an unexpected state rather than
            # returning a misleading None pool.
            raise

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
