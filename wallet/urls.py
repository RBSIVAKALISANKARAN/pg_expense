from django.urls import path

from .views import (
    account_detail,
    account_list_create,
    allocate_funds,
    deposit_funds,
    expense_create,
    transfer_to_savings,
    transfer_to_spendable,
    transactions_list,
    dashboard,
    docs,
    schema_view,
)

urlpatterns = [
    path('accounts/', account_list_create, name='account-list-create'),
    path('accounts/<uuid:id>/', account_detail, name='account-detail'),
    path('accounts/<uuid:id>/deposit/', deposit_funds, name='account-deposit'),
    path('accounts/<uuid:id>/allocate/', allocate_funds, name='account-allocate'),
    path('accounts/<uuid:id>/expense/', expense_create, name='account-expense'),
    path('accounts/<uuid:id>/transfer-to-savings/', transfer_to_savings, name='account-transfer-to-savings'),
    path('accounts/<uuid:id>/transfer-to-spendable/', transfer_to_spendable, name='account-transfer-to-spendable'),
    path('accounts/<uuid:id>/transactions/', transactions_list, name='account-transactions'),
    path('dashboard/', dashboard, name='dashboard'),
    path('docs/', docs, name='api-docs'),
    path('schema/', schema_view, name='api-schema'),
]
