import json

from rest_framework.exceptions import ValidationError

from .complete_flow_views import wallet_edit_expense, wallet_expense_entry
from .models import Transaction, TransactionType


TRANSPORT_FIELDS = (
    'transport_from', 'transport_to', 'transport_mode', 'bus_type', 'payment_method',
)


def _request_payload(request):
    """Return the request payload without wrapping a Django request in DRF twice."""
    if hasattr(request, 'data'):
        return request.data.copy()

    content_type = (request.META.get('CONTENT_TYPE') or '').split(';', 1)[0].strip().lower()
    if content_type == 'application/json':
        raw = request.body.decode(request.encoding or 'utf-8') if request.body else '{}'
        return json.loads(raw or '{}')

    return request.POST.copy()


def _request_with_defaults(request, values):
    """Merge persisted transport defaults into the incoming payload."""
    data = _request_payload(request)
    for key, value in values.items():
        if key not in data or data.get(key) in (None, ''):
            if value not in (None, ''):
                data[key] = value
    request._complete_flow_payload = data
    return request


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

    merged = _request_with_defaults(request, defaults)

    if hasattr(merged, 'data'):
        # Already a DRF Request. Inject the merged payload and invoke the target.
        merged._full_data = merged._complete_flow_payload
        return wallet_edit_expense(merged, id)

    # Plain Django request: do not wrap it here. The target @api_view wrapper
    # will perform the DRF conversion exactly once. Replace the raw JSON body
    # so the target view receives the merged payload.
    merged._body = json.dumps(merged._complete_flow_payload).encode(merged.encoding or 'utf-8')
    merged.META['CONTENT_LENGTH'] = str(len(merged._body))
    merged.META['CONTENT_TYPE'] = 'application/json'
    return wallet_edit_expense(merged, id)
