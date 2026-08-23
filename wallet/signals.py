from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Transaction


@receiver(pre_save, sender=Transaction)
def ensure_transaction_occurred_at(sender, instance, **kwargs):
    """Never allow API callers to override the model default with NULL."""
    if instance.occurred_at is None:
        instance.occurred_at = timezone.now()
