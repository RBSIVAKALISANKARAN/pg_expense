from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.urls import path

from .account_money_views import deposit_funds_fixed, transfer_allocation_fixed
from .complete_flow_fixes import complete_edit_expense
from .complete_flow_views import (
    complete_sql_page,
    create_wallet_account,
    exact_database_page,
    exact_sql_schema,
    money_report_data,
    wallet_expense_entry,
    wallet_transfer,
)
from .concurrency_guards import wallet_revert_transaction_safe
from .export_views import export_report
from .feature_views import expense_page, meals
from .location_features import enhanced_money_locations
from .phase4_views import (
    phase4_saved_queries,
    phase4_sql_history,
    phase4_sql_schema,
    phase4_transaction_filter_options,
    phase4_transaction_list,
)
from .power_override_views import power_override, power_override_page
from .savings_views import savings_analytics, savings_page
from .sql_security import sql_execute_secure
from .taxonomy_views import food_taxonomy
from .transaction_page import enhanced_transaction_page
from .views import (
    account_detail,
    account_list_create,
    accounts_page,
    categories_list_create,
    categories_page,
    dashboard,
    expense_create,
    food_profiles,
    items_list_create,
    money_locations_list,
    money_pools_list,
    owners_list,
    report_page,
    subcategories_list_create,
    summary_report,
    transactions_list,
)

urlpatterns = [
    path("accounts/", account_list_create, name="account-list-create"),
    path("accounts/page/", accounts_page, name="accounts-page"),
    path("accounts/<uuid:id>/", account_detail, name="account-detail"),
    path("accounts/<uuid:id>/deposit/", deposit_funds_fixed, name="account-deposit"),
    path(
        "accounts/<uuid:id>/allocate/",
        transfer_allocation_fixed,
        name="account-allocate",
    ),
    path("accounts/<uuid:id>/expense/", expense_create, name="account-expense"),
    path(
        "accounts/<uuid:id>/transfer-to-savings/",
        transfer_allocation_fixed,
        {"target_type": "savings"},
        name="account-transfer-to-savings",
    ),
    path(
        "accounts/<uuid:id>/transfer-to-spendable/",
        transfer_allocation_fixed,
        {"target_type": "spendable"},
        name="account-transfer-to-spendable",
    ),
    path(
        "accounts/<uuid:id>/transactions/",
        transactions_list,
        name="account-transactions",
    ),
    path("accounts/<uuid:id>/summary/", summary_report, name="account-summary"),
    path("accounts/<uuid:id>/export.csv/", export_report, name="account-export-csv"),
    path("categories/", categories_list_create, name="categories-list-create"),
    path("categories/page/", categories_page, name="categories-page"),
    path("subcategories/", subcategories_list_create, name="subcategories-list-create"),
    path("items/", items_list_create, name="items-list-create"),
    path("food-profiles/", food_profiles, name="food-profiles"),
    path("food-taxonomy/", food_taxonomy, name="food-taxonomy"),
    path("meals/", meals, name="meals"),
    path("owners/", owners_list, name="owners-list"),
    path("money-locations/", money_locations_list, name="money-locations-list"),
    path(
        "money-locations/enhanced/",
        enhanced_money_locations,
        name="enhanced-money-locations",
    ),
    path("money-pools/", money_pools_list, name="money-pools-list"),
    path(
        "wallet/accounts/create/", create_wallet_account, name="wallet-account-create"
    ),
    path("wallet/transfer/", wallet_transfer, name="wallet-transfer"),
    path("expense/entry/", wallet_expense_entry, name="wallet-expense-entry"),
    path(
        "transactions/<uuid:id>/edit/",
        complete_edit_expense,
        name="wallet-transaction-edit-expense",
    ),
    path(
        "transactions/<uuid:id>/revert/",
        wallet_revert_transaction_safe,
        name="wallet-transaction-revert",
    ),
    path(
        "reports/data/", login_required(money_report_data), name="wallet-reports-data"
    ),
    path("database/page/", exact_database_page, name="database-structure-page"),
    path("sql/", staff_member_required(complete_sql_page), name="sql-playground"),
    path(
        "sql/schema-live-exact/",
        staff_member_required(exact_sql_schema),
        name="sql-schema-live-exact",
    ),
    path("expense/page/", expense_page, name="expense-page"),
    path("transactions/all/", phase4_transaction_list, name="enhanced-transactions"),
    path(
        "transactions/filter-options/",
        phase4_transaction_filter_options,
        name="transaction-filter-options",
    ),
    path("power-override/page/", power_override_page, name="power-override-page"),
    path("power-override/", power_override, name="power-override"),
    path("dashboard/", dashboard, name="dashboard"),
    path("transactions/page/", enhanced_transaction_page, name="transactions-page"),
    path("reports/page/", report_page, name="reports-page"),
    path("savings/page/", savings_page, name="savings-page"),
    path("savings/analytics/", savings_analytics, name="savings-analytics"),
    path("sql/execute-live/", sql_execute_secure, name="sql-execute-live"),
    path("sql/schema-live/", phase4_sql_schema, name="sql-schema-live"),
    path("sql/execute/", sql_execute_secure, name="sql-execute"),
    path("sql/history/", phase4_sql_history, name="sql-history"),
    path("sql/saved/", phase4_saved_queries, name="sql-saved"),
    path("sql/schema/", phase4_sql_schema, name="sql-schema"),
]
