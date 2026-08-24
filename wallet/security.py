"""Authentication and security helpers for PG Expense.

The application is a private financial workspace. All application pages and
financial APIs require an authenticated Django session. Django admin keeps its
own authentication flow.
"""

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


PUBLIC_PATHS = {
    "/login/",
    "/logout/",
}

PUBLIC_PREFIXES = (
    "/static/",
    "/media/",
    "/admin/",
)


class AuthenticationRequiredMiddleware:
    """Require authentication for every PG Expense application endpoint.

    API requests receive JSON 401 responses; browser requests are redirected
    to the login page. Django admin retains its own authentication handling.
    The test runner bypass is only active while Django's test command is
    running; dedicated security tests explicitly disable it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.TESTING or self._is_public(request.path):
            return self.get_response(request)

        if not request.user.is_authenticated:
            if request.path.startswith("/api/"):
                return JsonResponse(
                    {"detail": "Authentication credentials were not provided."},
                    status=401,
                )
            login_url = reverse("login")
            return redirect(f"{login_url}?next={request.get_full_path()}")

        return self.get_response(request)

    @staticmethod
    def _is_public(path):
        return path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)
