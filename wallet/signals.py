from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Account, Allocation, AllocationType, Transaction


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
