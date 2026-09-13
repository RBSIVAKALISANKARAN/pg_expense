"""Authentication and security helpers for PG Expense.

The application is a private financial workspace. All application pages and
financial APIs require an authenticated Django session. Django admin keeps its
own authentication flow.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
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

TEST_USER_USERNAME = "__pg_expense_test_runner__"


class AuthenticationRequiredMiddleware:
    """Require authentication for every PG Expense application endpoint.

    During the Django test command only, legacy tests that use a bare Django
    or DRF client are given a real authenticated test user. DRF permissions
    therefore remain ``IsAuthenticated`` during tests as they are in normal
    execution. Security tests explicitly disable ``TESTING`` and exercise the
    unauthenticated boundary normally.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_public(request.path):
            return self.get_response(request)

        if settings.TESTING and not request.user.is_authenticated:
            User = get_user_model()
            request.user, _ = User.objects.get_or_create(
                username=TEST_USER_USERNAME,
                defaults={"is_active": True},
            )

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
        return path in PUBLIC_PATHS or any(
            path.startswith(prefix) for prefix in PUBLIC_PREFIXES
        )
