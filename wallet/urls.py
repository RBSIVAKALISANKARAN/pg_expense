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
from .sql_security import sql_execute_secure
from .feature_views import (
    expense_page, expense_entry, meals, transfer_between_accounts, revert_transaction,
    edit_expense, enhanced_transaction_list, enhanced_reports_page, report_data,
    enhanced_database_page, enhanced_sql_page, enhanced_sql_execute, sql_schema_data,
)
from .complete_flow_views import (
    create_wallet_account, wallet_transfer, wallet_expense_entry,
    wallet_edit_expense, wallet_revert_transaction, money_report_data,
    exact_database_page, complete_sql_page, exact_sql_schema,
)
from .complete_flow_fixes import complete_edit_expense
from .transaction_page import enhanced_transaction_page
from .location_features import enhanced_money_locations

urlpatterns = [
    path('accounts/', account_list_create, name='account-list-create'),
    path('accounts/page/', accounts_page, name='accounts-page'),
    path('accounts/<uuid:id>/', account_detail, name='account-detail'),
    path('accounts/<uuid:id>/deposit/', deposit_funds, name='account-deposit'),
    path('accounts/<uuid:id>/allocate/', allocate_funds, name='account-allocate'),
    path('accounts/<uuid:id>/expense/', expense_create, name='account-expense'),
    path('accounts/<uuid:id>/transfer-to-savings/', transfer_to_savings, name='account-transfer-to-savings'),
    path('accounts/<uuid:id>/transfer-to-spendable/', transfer_to_spendable, name='account-transfer-to-spendable'),
    path('accounts/<uuid:id>/transactions/', transactions_list, name='account-transactions'),
    path('accounts/<uuid:id>/summary/', summary_report, name='account-summary'),
    path('accounts/<uuid:id>/export.csv/', export_report, name='account-export-csv'),
    path('categories/', categories_list_create, name='categories-list-create'),
    path('categories/page/', categories_page, name='categories-page'),
    path('subcategories/', subcategories_list_create, name='subcategories-list-create'),
    path('items/', items_list_create, name='items-list-create'),
    path('food-profiles/', food_profiles, name='food-profiles'),
    path('meals/', meals, name='meals'),
    path('owners/', owners_list, name='owners-list'),
    path('money-locations/', money_locations_list, name='money-locations-list'),
    path('money-locations/enhanced/', enhanced_money_locations, name='enhanced-money-locations'),
    path('money-pools/', money_pools_list, name='money-pools-list'),

    # Complete money-flow implementation. These routes intentionally precede the older feature routes.
    path('wallet/accounts/create/', create_wallet_account, name='wallet-account-create'),
    path('wallet/transfer/', wallet_transfer, name='wallet-transfer'),
    path('expense/entry/', wallet_expense_entry, name='wallet-expense-entry'),
    path('transactions/<uuid:id>/edit/', complete_edit_expense, name='wallet-transaction-edit-expense'),
    path('transactions/<uuid:id>/revert/', wallet_revert_transaction, name='wallet-transaction-revert'),
    path('reports/data/', money_report_data, name='wallet-reports-data'),
    path('database/page/', exact_database_page, name='database-structure-page'),
    path('sql/', complete_sql_page, name='sql-playground'),
    path('sql/schema-live-exact/', exact_sql_schema, name='sql-schema-live-exact'),

    path('expense/page/', expense_page, name='expense-page'),
    path('expense/entry-legacy/', expense_entry, name='expense-entry-legacy'),
    path('transfer/money/', transfer_between_accounts, name='transfer-money-legacy'),
    path('transactions/all/', enhanced_transaction_list, name='enhanced-transactions'),
    path('settings/', app_settings, name='app-settings'),
    path('settings/page/', settings_page, name='settings-page'),
    path('dashboard/', dashboard, name='dashboard'),
    path('transactions/page/', enhanced_transaction_page, name='transactions-page'),
    path('reports/page/', enhanced_reports_page, name='reports-page'),
    path('sql/execute-live/', enhanced_sql_execute, name='sql-execute-live'),
    path('sql/schema-live/', exact_sql_schema, name='sql-schema-live'),
    path('sql/execute/', sql_execute_secure, name='sql-execute'),
    path('sql/history/', sql_history, name='sql-history'),
    path('sql/saved/', sql_saved_queries, name='sql-saved-queries'),
    path('sql/saved/<uuid:id>/', sql_saved_queries, name='sql-saved-query-detail'),
    path('sql/schema/', sql_schema, name='sql-schema'),
    path('docs/', docs, name='api-docs'),
    path('schema/', schema_view, name='api-schema'),
]
