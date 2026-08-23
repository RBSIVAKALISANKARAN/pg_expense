from copy import deepcopy

from rest_framework.exceptions import ValidationError

from .complete_flow_views import wallet_edit_expense, wallet_expense_entry
from .models import Transaction, TransactionType


TRANSPORT_FIELDS = (
    'transport_from', 'transport_to', 'transport_mode', 'bus_type', 'payment_method',
)


def _request_with_defaults(request, values):
    """Make a mutable copy of request.data without changing the original request."""
    data = request.data.copy()
    for key, value in values.items():
        if key not in data or data.get(key) in (None, ''):
            if value not in (None, ''):
                data[key] = value
    request._full_data = data
    return request


def complete_expense_entry(request):
    """Compatibility wrapper; Transaction signal supplies a timestamp if omitted."""
    return wallet_expense_entry(request)


def complete_edit_expense(request, id):
    """Allow partial edits while preserving existing transport metadata.

    The normal edit endpoint accepts PATCH/PUT. For a transport transaction,
    changing only the amount/category/etc. should not require the user to
    resend From/To/payment details that are already stored on the transaction.
    """
    tx = Transaction.objects.filter(pk=id, type=TransactionType.EXPENSE).first()
    if not tx:
        raise ValidationError('Only existing expense transactions can be edited.')

    metadata = tx.metadata or {}
    defaults = {key: metadata.get(key) for key in TRANSPORT_FIELDS}
    defaults['merchant'] = metadata.get('merchant')
    defaults['note'] = metadata.get('note')
    defaults['custom_description'] = metadata.get('custom_description')
    return wallet_edit_expense(_request_with_defaults(request, defaults), id)
