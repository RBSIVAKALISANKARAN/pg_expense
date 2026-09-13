from functools import wraps

from django.http import HttpResponseForbidden
from rest_framework import status
from rest_framework.response import Response


def staff_only_page(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return HttpResponseForbidden("Staff access is required for the SQL playground.")
        return view(request, *args, **kwargs)

    return wrapped


def staff_only_api(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not request.user.is_staff:
            return Response(
                {"detail": "Staff access is required for the SQL playground."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return view(request, *args, **kwargs)

    return wrapped
