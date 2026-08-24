"""URL configuration for PG Expense."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/api/dashboard/", permanent=False)),
    path("login/", include("wallet.auth_urls")),
    path("admin/", admin.site.urls),
    path("api/", include("wallet.urls")),
]
