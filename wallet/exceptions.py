"""Consistent error envelope for the API.

FINAL response-shape decision: this project does not wrap successful responses.
Success responses remain the resource itself (a list, dict, or a simple
``{"detail": ...}`` response). The frontend already depends on those domain
shapes, so adding a ``{"data": ...}`` wrapper would be a breaking change with
no functional benefit for this project.

Every error response is normalized to a two-key envelope:

    {"detail": "<human-readable message>", "errors": {...}}

``errors`` is always present. It is empty for errors that carry no
field-level detail (e.g. PermissionDenied, NotAuthenticated, NotFound,
unhandled 500s) and contains the structured validation payload otherwise.
"""

from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        # Unhandled exception types (e.g. a bare Python exception DRF
        # doesn't recognize) fall through to Django's own 500 handling.
        return response

    data = response.data

    # Already in the target shape (has both keys) - leave it alone.
    if isinstance(data, dict) and "detail" in data and "errors" in data:
        return response

    # Bare {"detail": "..."} from DRF built-ins (PermissionDenied, NotFound,
    # NotAuthenticated, Throttled, ...) or from a manual Response. Add the
    # empty errors key so every error response has the same top-level shape.
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        response.data = {
            "detail": str(data["detail"]),
            "errors": {},
        }
        return response

    # Field-keyed validation errors: {"field": ["msg", ...], ...}
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