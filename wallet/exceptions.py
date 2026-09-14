"""Consistent error envelope for the API.

FINAL response-shape decision: this project does not wrap successful responses.
Success responses remain the resource itself (a list, dict, or a simple
``{"detail": ...}`` response). The frontend already depends on those domain
shapes, so adding a ``{"data": ...}`` wrapper would be a breaking change with
no functional benefit for this project.

Errors are normalized to a top-level ``detail`` string. When the underlying
error contains field-level or structured details, they are preserved under
``errors`` so clients can still use them for validation feedback.
"""

from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        # Unhandled exception types (e.g. a bare Python exception DRF
        # doesn't recognize) fall through to Django's own 500 handling,
        # same as before this handler existed.
        return response

    data = response.data
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        # Already in the target shape - most manual `Response({"detail": ...})`
        # calls and DRF's built-in exceptions (NotAuthenticated, PermissionDenied,
        # NotFound, Throttled, ...) land here untouched.
        return response

    if isinstance(data, dict):
        first_message = next(iter(data.values()), None)
        if isinstance(first_message, list) and first_message:
            first_message = first_message[0]
        response.data = {
            "detail": str(first_message) if first_message else "Request could not be processed.",
            "errors": data,
        }
    elif isinstance(data, list):
        response.data = {
            "detail": str(data[0]) if data else "Request could not be processed.",
            "errors": data,
        }

    return response
