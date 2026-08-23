from copy import deepcopy
from decimal import Decimal

from django.http import QueryDict
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from .complete_flow_views import wallet_edit_expense, wallet_expense_entry
from .models import Transaction, TransactionType


TRANSPORT_FIELDS = (
    'transport_from', 'transport_to', 'transport_mode', 'bus_type', 'payment_method',
)


def _request_with_defaults(request, values):
    """Return a DRF Request with a mutable merged payload.

    Django's test client can invoke the URL resolver with a plain WSGIRequest,
    while DRF's ``@api_view`` machinery normally supplies a DRF Request. The
    wrapper must support both so PATCH requests behave identically in tests and
    in production.
    """
    source = getattr(request, 'data', None)
    if source is None:
        # The request is a plain Django request. Parse the already-decoded body
        # through DRF's Request before merging defaults.
        request = Request(request)
        source = request.data

    if hasattr(source, 'copy'):
        data = source.copy()
    else:
        data = dict(source or {})

    for key, value in values.items():
        if key not in data or data.get(key) in (None, ''):
            if value not in (None, ''):
                data[key] = value

    # Preserve the request metadata while replacing the parsed payload.
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
