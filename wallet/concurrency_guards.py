from django.db import transaction
from rest_framework.decorators import api_view

from .complete_flow_views import wallet_revert_transaction as _wallet_revert_transaction
from .models import Account, Transaction


@api_view(['POST', 'DELETE'])
def wallet_revert_transaction_safe(request, id):
    """Pre-lock a transaction pair and their accounts in deterministic order.

    Transfer reverts can touch two transactions and two accounts. Without a
    stable lock order, two opposite concurrent reverts can deadlock while each
    request holds the first transaction/account needed by the other request.
    """
    with transaction.atomic():
        transaction_ids = [id]
        related_id = (
            Transaction.objects.filter(pk=id).values_list('related_tx_id', flat=True).first()
        )
        if related_id:
            transaction_ids.append(related_id)

        transaction_ids = sorted({str(value) for value in transaction_ids})
        locked_transactions = list(
            Transaction.objects.select_for_update().filter(pk__in=transaction_ids).order_by('pk')
        )
        if not locked_transactions:
            return _wallet_revert_transaction(request, id)

        account_ids = sorted({str(tx.account_id) for tx in locked_transactions})
        list(
            Account.objects.select_for_update()
            .filter(pk__in=account_ids)
            .order_by('pk')
        )

        return _wallet_revert_transaction(request, id)
