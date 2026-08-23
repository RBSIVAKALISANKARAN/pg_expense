from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from .complete_flow_views import wallet_edit_expense, wallet_expense_entry
from .models import Transaction, TransactionType


TRANSPORT_FIELDS = (
    'transport_from', 'transport_to', 'transport_mode', 'bus_type', 'payment_method',
)


def _request_with_defaults(request, values):
    """Return a DRF Request with a merged payload for PATCH/PUT edits.

    Django's URL resolver can hand this wrapper a plain WSGIRequest. When that
    happens, the request body has not yet been parsed by DRF. The safest path
    is to read the raw body as JSON/form data ourselves, merge the persisted
    defaults, and build a fresh DRF Request with a parser-compatible payload.
    """
    if isinstance(request, Request):
        source = request.data.copy()
        for key, value in values.items():
            if key not in source or source.get(key) in (None, ''):
                if value not in (None, ''):
                    source[key] = value
        request._full_data = source
        return request

    # Plain Django WSGIRequest: use the already-decoded body for JSON requests.
    import json

    content_type = (request.META.get('CONTENT_TYPE') or '').split(';', 1)[0].strip().lower()
    if content_type == 'application/json':
        raw = request.body.decode(request.encoding or 'utf-8') if request.body else '{}'
        source = json.loads(raw or '{}')
    else:
        source = request.POST.copy()

    for key, value in values.items():
        if key not in source or source.get(key) in (None, ''):
            if value not in (None, ''):
                source[key] = value

    drf_request = Request(request)
    drf_request._full_data = source
    return drf_request


def complete_expense_entry(request):
    """Compatibility wrapper; Transaction signal supplies a timestamp if omitted."""
    return wallet_expense_entry(request)


def complete_edit_expense(request, id):
    """Allow partial edits while preserving existing transport metadata."""
    tx = Transaction.objects.filter(pk=id, type=TransactionType.EXPENSE).first()
    if not tx:
        raise ValidationError('Only existing expense transactions can be edited.')

    metadata = tx.metadata or {}
    defaults = {key: metadata.get(key) for key in TRANSPORT_FIELDS}
    defaults['merchant'] = metadata.get('merchant')
    defaults['note'] = metadata.get('note')
    defaults['custom_description'] = metadata.get('custom_description')
    return wallet_edit_expense(_request_with_defaults(request, defaults), id)
