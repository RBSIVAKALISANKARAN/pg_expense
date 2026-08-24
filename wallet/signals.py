from decimal import Decimal

from django.db.models.signals import post_migrate, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Account, Allocation, AllocationType, MoneyLocation, MoneyPool, Owner, Transaction


STANDARD_OWNERS = ('Me', 'Appa', 'Amma')
STANDARD_LOCATIONS = (
    ('rbsankaran_acc', 'bank'),
    ('Amma Cash', 'cash'),
    ('Appa Cash', 'cash'),
    ('Change Cash', 'change_cash'),
    ('Travel Card', 'travel_card'),
)


@receiver(pre_save, sender=Transaction)
def ensure_transaction_occurred_at(sender, instance, **kwargs):
    """Never allow API callers to override the model default with NULL."""
    if instance.occurred_at is None:
        instance.occurred_at = timezone.now()


@receiver(post_save, sender=Account)
def ensure_account_allocations(sender, instance, created, **kwargs):
    """Every account has the two canonical allocation buckets."""
    if created:
        for allocation_type in (AllocationType.SPENDABLE, AllocationType.SAVINGS):
            Allocation.objects.get_or_create(account=instance, type=allocation_type)


def ensure_standard_wallets():
    """Restore the non-user-specific standard wallet records.

    Django's test ``flush`` removes data after migrations have run, so a
    data-migration alone cannot guarantee that standard wallets exist for every
    TestCase.  The same idempotent initializer is also useful for a development
    database that has been flushed.  It never overwrites balances.
    """
    for owner_name in STANDARD_OWNERS:
        Owner.objects.get_or_create(name=owner_name, defaults={'active': True})

    owner = Owner.objects.get(name='Me')

    for location_name, location_type in STANDARD_LOCATIONS:
        location, _ = MoneyLocation.objects.get_or_create(
            name=location_name,
            defaults={'location_type': location_type, 'active': True},
        )
        changed = []
        if location.location_type != location_type:
            location.location_type = location_type
            changed.append('location_type')
        if not location.active:
            location.active = True
            changed.append('active')
        if changed:
            location.save(update_fields=changed + ['updated_at'])

        account, _ = Account.objects.get_or_create(
            name=location_name,
            defaults={
                'money_location': location,
                'currency': 'INR',
                'total_balance': Decimal('0'),
            },
        )
        if account.money_location_id != location.id:
            account.money_location = location
            account.save(update_fields=['money_location', 'updated_at'])

        for allocation_type in (AllocationType.SPENDABLE, AllocationType.SAVINGS):
            allocation, _ = Allocation.objects.get_or_create(
                account=account,
                type=allocation_type,
                defaults={'balance': Decimal('0')},
            )
            MoneyPool.objects.get_or_create(
                account=account,
                owner=owner,
                location=location,
                allocation_type=allocation_type,
                defaults={'current_amount': allocation.balance},
            )


@receiver(post_migrate)
def seed_standard_wallets_after_migrate(sender, app_config, **kwargs):
    """Make standard wallets available after migrations and test-db flushes."""
    if app_config is not None and app_config.label != 'wallet':
        return
    ensure_standard_wallets()
