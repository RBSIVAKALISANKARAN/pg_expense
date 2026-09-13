from django.db import transaction

from .complete_flow_views import \
    wallet_revert_transaction as _wallet_revert_transaction
from .models import Account, Transaction


def wallet_revert_transaction_safe(request, id):
    """Pre-lock a transaction pair and their accounts in deterministic order."""
    with transaction.atomic():
        transaction_ids = [id]
        related_id = (
            Transaction.objects.filter(pk=id)
            .values_list("related_tx_id", flat=True)
            .first()
        )
        if related_id:
            transaction_ids.append(related_id)

        transaction_ids = sorted({str(value) for value in transaction_ids})
        locked_transactions = list(
            Transaction.objects.select_for_update()
            .filter(pk__in=transaction_ids)
            .order_by("pk")
        )
        if locked_transactions:
            account_ids = sorted({str(tx.account_id) for tx in locked_transactions})
            list(
                Account.objects.select_for_update()
                .filter(pk__in=account_ids)
                .order_by("pk")
            )

        return _wallet_revert_transaction(request, id)
