"""Domain logic for accounts, allocations, and money pools.

This was previously a block of private (``_``-prefixed) helper functions
living inside ``views.py`` and imported from there by several other view
modules. Views calling into other views' private helpers is a sign the
logic doesn't belong to any one view - it's shared domain behavior, so it
lives here instead. Views should stay thin: parse the request, call into
this module, serialize the result.

Nothing here talks HTTP (no ``Response``, no ``request``); the one
exception is raising DRF's ``ValidationError``, which is kept because it's
the shared vocabulary the views already use to turn a domain rule
violation into a 400 response, and re-catching/re-raising a different
exception type at every call site would be pure ceremony for no benefit.
"""

from decimal import Decimal

from django.db.models import F, Sum
from rest_framework.exceptions import ValidationError

from .models import Allocation, AllocationType, MoneyLocation, MoneyPool, Owner


def ensure_allocations(account):
    """Guarantee both allocation rows (spendable/savings) exist for an account."""
    for allocation_type in (AllocationType.SPENDABLE, AllocationType.SAVINGS):
        Allocation.objects.get_or_create(account=account, type=allocation_type)
    return account.allocations.all()


def ensure_family_defaults():
    """Seed the standard set of owners and money locations if missing."""
    for owner_name in ["Me", "Appa", "Amma"]:
        Owner.objects.get_or_create(name=owner_name, defaults={"active": True})
    for location_name, location_type in [
        ("rbsankaran_acc", "bank"),
        ("Appa Cash", "cash"),
        ("Amma Cash", "cash"),
        ("Change Cash", "change_cash"),
        ("Travel Card", "travel_card"),
    ]:
        MoneyLocation.objects.get_or_create(
            name=location_name,
            defaults={"location_type": location_type, "active": True},
        )


def default_owner_and_location():
    ensure_family_defaults()
    owner, _ = Owner.objects.get_or_create(name="Me", defaults={"active": True})
    location = MoneyLocation.objects.filter(name="rbsankaran_acc").first()
    if location is None:
        location = MoneyLocation.objects.create(
            name="rbsankaran_acc", location_type="bank", active=True
        )
    return owner, location


def account_context(account, requested_owner=None, requested_location=None):
    """Resolve (and validate) the owner/location an account operation applies to."""
    default_owner, default_location = default_owner_and_location()
    owner = requested_owner or default_owner
    location = requested_location or account.money_location or default_location
    if not owner.active:
        raise ValidationError("The selected owner is inactive.")
    if not location.active:
        raise ValidationError("The selected money location is inactive.")
    if account.money_location_id and account.money_location_id != location.id:
        raise ValidationError(
            "The supplied money location does not belong to this account."
        )
    if not account.money_location_id:
        account.money_location = location
        account.save(update_fields=["money_location", "updated_at"])
    return owner, location


def _allocation_type_value(allocation_or_type):
    if isinstance(allocation_or_type, Allocation):
        return allocation_or_type.type
    return allocation_or_type


def ensure_money_pool(account, owner, location, allocation_or_type, lock=False):
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
            current_amount=Decimal("0"),
        )
    return MoneyPool.objects.select_for_update().get(pk=pool.pk) if lock else pool


def sync_account_pools(account, owner, location):
    ensure_allocations(account)
    spendable = Allocation.objects.get(account=account, type=AllocationType.SPENDABLE)
    savings = Allocation.objects.get(account=account, type=AllocationType.SAVINGS)
    spendable_pool = ensure_money_pool(account, owner, location, spendable)
    savings_pool = ensure_money_pool(account, owner, location, savings)
    if spendable_pool.current_amount == 0 and spendable.balance != 0:
        spendable_pool.current_amount = spendable.balance
        spendable_pool.save(update_fields=["current_amount", "updated_at"])
    if savings_pool.current_amount == 0 and savings.balance != 0:
        savings_pool.current_amount = savings.balance
        savings_pool.save(update_fields=["current_amount", "updated_at"])
    return spendable_pool, savings_pool


def apply_money_pool_delta(account, owner, location, allocation_or_type, delta):
    allocation_type = _allocation_type_value(allocation_or_type)
    if owner is None or location is None or allocation_type is None:
        return None
    pool = ensure_money_pool(account, owner, location, allocation_type, lock=True)
    if pool is None:
        return None
    if pool.current_amount + delta < 0:
        raise ValidationError("Money pool balance cannot go below zero.")
    if delta == Decimal("0"):
        return pool
    pool.current_amount = F("current_amount") + delta
    pool.save(update_fields=["current_amount", "updated_at"])
    pool.refresh_from_db()
    return pool


def check_pool_funds(account, owner, location, allocation_or_type, amount):
    allocation_type = _allocation_type_value(allocation_or_type)
    if owner is None or location is None or allocation_type is None:
        return
    pool = ensure_money_pool(account, owner, location, allocation_type, lock=True)
    if pool is None:
        return
    pool.refresh_from_db()
    if pool.current_amount < amount:
        raise ValidationError("Insufficient funds in this specific owner's money pool.")


def assert_account_reconciles(account):
    """Raise if an account's total balance doesn't match its allocations/pools.

    Called at the end of every money-moving operation as a last line of
    defense: if this ever fails, the surrounding transaction is rolled
    back and nothing is persisted.
    """
    allocation_total = account.allocations.aggregate(total=Sum("balance"))[
        "total"
    ] or Decimal("0")
    pool_total = account.money_pools.aggregate(total=Sum("current_amount"))[
        "total"
    ] or Decimal("0")
    if account.total_balance != allocation_total:
        raise ValidationError(
            "Account allocation reconciliation failed; no changes were saved."
        )
    if account.total_balance != pool_total:
        raise ValidationError(
            "Account money-pool reconciliation failed; no changes were saved."
        )
