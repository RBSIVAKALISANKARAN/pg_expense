from django.urls import path

from .views import (
    account_detail, account_list_create, accounts_page, allocate_funds, app_settings,
    categories_list_create, categories_page, database_structure_page, deposit_funds,
    expense_create, food_profiles, items_list_create, money_locations_list,
    money_pools_list, owners_list, settings_page, subcategories_list_create,
    report_page, transfer_to_savings, transfer_to_spendable, transactions_list,
    transactions_page, summary_report, export_report, dashboard, docs, schema_view,
    sql_execute, sql_history, sql_playground, sql_saved_queries, sql_schema,
)
from .feature_views import (
    expense_page, expense_entry, meals, transfer_between_accounts, revert_transaction,
    edit_expense, enhanced_transaction_list, enhanced_reports_page, report_data,
    enhanced_database_page, enhanced_sql_page, enhanced_sql_execute, sql_schema_data,
)
from .transaction_page import enhanced_transaction_page
from .location_features import enhanced_money_locations

urlpatterns = [
    path('accounts/', account_list_create, name='account-list-create'), path('accounts/page/', accounts_page, name='accounts-page'), path('accounts/<uuid:id>/', account_detail, name='account-detail'),
    path('accounts/<uuid:id>/deposit/', deposit_funds, name='account-deposit'), path('accounts/<uuid:id>/allocate/', allocate_funds, name='account-allocate'), path('accounts/<uuid:id>/expense/', expense_create, name='account-expense'),
    path('accounts/<uuid:id>/transfer-to-savings/', transfer_to_savings, name='account-transfer-to-savings'), path('accounts/<uuid:id>/transfer-to-spendable/', transfer_to_spendable, name='account-transfer-to-spendable'), path('accounts/<uuid:id>/transactions/', transactions_list, name='account-transactions'), path('accounts/<uuid:id>/summary/', summary_report, name='account-summary'), path('accounts/<uuid:id>/export.csv/', export_report, name='account-export-csv'),
    path('categories/', categories_list_create, name='categories-list-create'), path('categories/page/', categories_page, name='categories-page'), path('subcategories/', subcategories_list_create, name='subcategories-list-create'), path('items/', items_list_create, name='items-list-create'), path('food-profiles/', food_profiles, name='food-profiles'), path('meals/', meals, name='meals'),
    path('owners/', owners_list, name='owners-list'), path('money-locations/', money_locations_list, name='money-locations-list'), path('money-locations/enhanced/', enhanced_money_locations, name='enhanced-money-locations'), path('money-pools/', money_pools_list, name='money-pools-list'),
    path('expense/page/', expense_page, name='expense-page'), path('expense/entry/', expense_entry, name='expense-entry'), path('transfer/money/', transfer_between_accounts, name='transfer-money'), path('transactions/all/', enhanced_transaction_list, name='enhanced-transactions'), path('transactions/<uuid:id>/revert/', revert_transaction, name='transaction-revert'), path('transactions/<uuid:id>/edit/', edit_expense, name='transaction-edit-expense'),
    path('settings/', app_settings, name='app-settings'), path('settings/page/', settings_page, name='settings-page'), path('dashboard/', dashboard, name='dashboard'), path('transactions/page/', enhanced_transaction_page, name='transactions-page'), path('reports/page/', enhanced_reports_page, name='reports-page'), path('reports/data/', report_data, name='reports-data'), path('database/page/', enhanced_database_page, name='database-structure-page'),
    path('sql/', enhanced_sql_page, name='sql-playground'), path('sql/execute-live/', enhanced_sql_execute, name='sql-execute-live'), path('sql/schema-live/', sql_schema_data, name='sql-schema-live'), path('sql/execute/', sql_execute, name='sql-execute'), path('sql/history/', sql_history, name='sql-history'), path('sql/saved/', sql_saved_queries, name='sql-saved-queries'), path('sql/saved/<uuid:id>/', sql_saved_queries, name='sql-saved-query-detail'), path('sql/schema/', sql_schema, name='sql-schema'), path('docs/', docs, name='api-docs'), path('schema/', schema_view, name='api-schema'),
]
