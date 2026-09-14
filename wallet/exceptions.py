"""Consistent error envelope for the API.

DRF's default exception handler already normalizes most errors (auth
failures, permission denials, 404s, and every ``{"detail": ...}`` response
this codebase raises by hand) to a single ``detail`` string. The one
exception is serializer validation errors, which come back field-keyed,
e.g. ``{"amount": ["This field must be a positive number."]}``.

That split means a client can't rely on ``response.data.detail`` always
being present on a 4xx/5xx response - sometimes it has to inspect field
keys instead. This handler closes that gap: every error response gets a
top-level ``detail`` string, and if the underlying error was field-keyed,
those are preserved verbatim under ``errors`` so form UIs can still
highlight the specific field.

This intentionally does not touch success response shapes. Every existing
endpoint currently returns whichever DRF/Serializer output it always has,
and the templates' JS already depends on those exact shapes - wrapping
success responses in a new envelope would be a breaking change across
every page, not just an error-handling cleanup, and needs its own
coordinated frontend pass rather than being folded in here.
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
