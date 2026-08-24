from decimal import Decimal

from django.db import IntegrityError

from .models import MoneyPool


def ensure_account_money_pool(account, owner, location, allocation_type, lock=False):
    """Return the money pool belonging to this exact account context.

    Account is part of the identity. Two accounts may legitimately use the same
    owner and money location, but their balances must never share a pool.
    """
    if owner is None or location is None or allocation_type is None:
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
