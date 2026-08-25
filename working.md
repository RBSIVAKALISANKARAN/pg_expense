# PG Expense — Complete Working Documentation

> **Purpose:** This document is the long-form working map of the PG Expense project: why it exists, how it was planned, how the architecture evolved, how money is represented, how the database is designed, how the APIs work, how the UI talks to the backend, how the SQL Playground works, what each phase delivered, and what remains to be fixed.
>
> **Working branch:** `demo`
>
> **Current focus:** Phase 7 remediation and browser/E2E validation.

---

# 1. Project Overview

PG Expense is a personal/family finance management application built around a real PostgreSQL database rather than a spreadsheet-style mockup.

The system combines four major purposes:

1. **Financial management** — wallets/accounts, deposits, expenses, transfers and savings.
2. **Financial classification** — categories, subcategories, items, variants and food-related metadata.
3. **Financial analysis** — dashboard, transaction ledger, reports and savings analytics.
4. **Database learning** — a safe SQL Playground, schema explorer, saved queries and query history against the same PostgreSQL database used by the application.

The application is intentionally designed so that the database is the source of truth. The UI does not maintain an independent financial state.

The core accounting invariant is:

```text
Account.total_balance
    = sum(Account allocations)
    = sum(Account MoneyPool current_amounts)
```

For the standard two-allocation model this becomes:

```text
Spendable + Savings = Total Account Balance
```

Savings is therefore **not another wallet containing duplicated money**. It is an earmarked allocation of the same account balance.

---

# 2. Original Product Direction

The original requirement was to build a practical expense-management system that could represent real money held in different payment sources and allow that money to be divided between normal spending and savings.

The system was deliberately expanded beyond a basic CRUD expense tracker because the intended application needed:

- real wallet/account balances
- allocation-aware spending
- owner and physical money-location tracking
- an auditable transaction ledger
- master data for categories and items
- food/event classification
- savings analytics
- reporting
- database exploration
- a SQL practice environment
- responsive application pages
- automated browser verification

The design process therefore moved from requirements clarification → money model → database model → business rules → API contracts → UI → security/integrity hardening → automated validation.

---

# 3. Technology Stack

## Backend

- Python
- Django
- Django REST Framework
- PostgreSQL

## Frontend

- Django templates
- HTML
- CSS
- JavaScript
- Fetch API
- No frontend framework is required for the current application shell.

## Authentication

- Django session authentication
- Django LoginView / LogoutView
- DRF SessionAuthentication
- authenticated application/API boundary

## Testing

- Django test runner for backend/regression tests
- pytest
- Playwright for real-browser Phase 7 E2E tests

## Database

- PostgreSQL
- `Decimal`-based monetary values
- UUID primary keys for financial/master entities
- database constraints plus application-level integrity checks

## Development environment

The project is developed locally from `C:\pg_expense` on the `demo` branch.

---

# 4. Repository and Application Structure

The main Django project contains:

```text
manage.py
pg_expense/
    settings.py
    urls.py
    asgi.py
    wsgi.py
wallet/
    models.py
    serializers.py
    views.py
    urls.py
    migrations/
    reporting.py
    savings_views.py
    account_money_views.py
    financial_integrity.py
    sql_security.py
    feature_views.py
    complete_flow_views.py
    phase4_views.py
    transaction_page.py
    export_views.py
    ...
pg_expense/templates/
    dashboard.html
    accounts.html
    expense.html
    transactions.html / related transaction templates
    categories.html
    reports.html
    savings.html
    sql playground templates
    database structure templates
    registration/login.html

e2e/
    test_phase7.py

Documentation:
    plan.md
    working.md
    API_DOCS.md
    NOTES.md
    PHASE_0_BASELINE.md
    PHASE_1_SECURITY.md
    PHASE_2_FINANCIAL_INTEGRITY.md
    PHASE_3_UI_COMPLETION.md
    PHASE_4_SEARCH_SQL.md
    PHASE_5_SAVINGS.md
    PHASE_6_MASTER_DATA.md
```

There are also historical/alternate implementations in the codebase. During remediation, routes and dependencies are traced before removing legacy code. The project intentionally avoids deleting working financial logic merely to make the repository look smaller.

---

# 5. Development and Phase Strategy

The project was developed as a sequence of controlled phases rather than changing the entire application at once.

The phase strategy is:

```text
Baseline
   ↓
Security / authentication
   ↓
Financial integrity
   ↓
Core UI completion
   ↓
Search + SQL Playground
   ↓
Savings analytics / master data / configuration work
   ↓
Browser/E2E validation
   ↓
Production hardening
   ↓
Final QA / release
```

The repository documentation records the concrete implementation phases as Phase 0 through Phase 6 and the broader project plan continues into Phase 7–9.

The current work is specifically **Phase 7 fix/validation**, including fixing the Accounts browser workflow and removing the Settings page as required by the current remediation plan.

---

# 6. Phase 0 — Baseline and Safety

Phase 0 established the remediation baseline on `demo`.

Recorded baseline:

- Repository: `RBSIVAKALISANKARAN/pg_expense`
- Branch: `demo`
- Baseline commit: `5f9021f599d8939bf2efe1f89b97c9212e63358a`
- Baseline date recorded in the phase document: 2026-08-24
- Main application: `wallet`
- Backend: Django + DRF
- Database: PostgreSQL
- Time zone: `Asia/Kolkata`

Safety rules established:

- work on `demo`, not `main`, during remediation
- do not redesign working financial logic without a requirement and regression test
- do not create a second financial database/model
- trace legacy routes before deleting them
- preserve historical migrations
- keep remediation changes controlled and testable

Known security findings were recorded for later remediation rather than silently changing the baseline.

---

# 7. Phase 1 — Security and Access Control

Phase 1 established the application's authentication and security boundary.

## Authentication

The browser application uses Django session authentication.

Important routes:

```text
/login/
/logout/
```

Application pages and `/api/` endpoints require authentication.

Unauthenticated API access is rejected with an HTTP 401 JSON response rather than exposing financial data.

Django `/admin/` retains Django's independent authentication system.

## Authorization scope

The current product is treated as one private household financial workspace.

The `Account` model does not currently contain a Django User foreign key. The project therefore deliberately does not invent row-level per-user ownership semantics.

A future multi-user version could add explicit user ownership, but that is a separate architectural change.

## Secrets

- database credentials come from environment configuration
- `.env` is ignored by Git
- no committed database password should exist
- `SECRET_KEY` is environment-driven, with development fallback behavior

## Django security configuration

The project also introduced configurable:

- allowed hosts
- CSRF trusted origins
- secure session/CSRF cookies
- HTTPS redirect behavior
- HttpOnly/SameSite cookie behavior

## SQL security

The SQL Playground is not protected merely by a Python keyword list. The secure executor additionally uses PostgreSQL's read-only transaction mode and a statement timeout.

---

# 8. Phase 2 — Financial Integrity and Data Safety

Phase 2 hardened the money engine without replacing the underlying accounting model.

The critical invariant became:

```text
Account.total_balance
    == SUM(Allocation.balance)
    == SUM(Account.money_pools.current_amount)
```

Money-changing operations run inside `transaction.atomic()`.

Affected balance rows are locked using `select_for_update()` to prevent concurrent requests from corrupting balances or allowing race-condition overspending.

The MoneyPool uniqueness model was corrected to be **account-scoped**:

```text
(account, owner, location, allocation_type)
```

This is important because two different accounts may represent money belonging to the same owner at the same physical location without sharing the same balance.

Regression coverage was added for:

- account isolation
- savings/spendable transfers
- expenses and reversals
- insufficient funds
- concurrent overspending

---

# 9. Phase 3 — Core UI Completion

Phase 3 completed important product-facing UI behavior.

## Settings persistence

An `AppSetting` model was introduced to persist application configuration.

Settings originally became a real database-backed page rather than a static UI.

## Savings/Spendable controls

The Accounts UI was connected to the transactional allocation endpoints.

The browser does not directly alter balances. It sends requests to the backend, and the backend performs the financial operation atomically.

## Dashboard

Dashboard responsibility was narrowed to:

- financial overview
- wallets
- recent activity
- navigation

Master-data creation was moved to the Categories/master-data area.

## Reports

The Reports page was converted from placeholder content into live ledger-backed analytics.

## Transactions

The transaction page received:

- loading states
- empty states
- error handling
- refresh behavior
- validation
- edit/revert/delete controls
- safe API-derived rendering

---

# 10. Phase 4 — Search, Filtering and SQL Playground

Phase 4 completed the transaction search/filtering workflow and hardened the SQL Playground.

## Transaction search

The ledger supports global search across relevant transaction fields including:

- wallet/account
- owner
- money location
- category
- subcategory
- item
- variant
- merchant
- note
- custom description
- transaction type

Filters include:

- wallet
- owner
- transaction type
- category
- allocation
- date range

Results are capped to avoid unbounded responses.

## SQL schema explorer

The application can query live PostgreSQL metadata and show:

- tables
- columns
- relationships/structure information

## Saved queries and history

The SQL Playground supports:

- executing read-only queries
- query history
- saved queries
- schema exploration

Saved queries use the same read-only validation rules as query execution.

---

# 11. Phase 5 — Savings Tracking and Analytics Foundation

Savings analytics were deliberately built from the existing `Transaction` table rather than creating a second savings ledger.

This is a key architectural decision:

> **Transaction is the historical source of truth; Allocation is the current balance state.**

Savings movements are classified from transaction semantics.

Examples:

```text
Deposit allocated to Savings       → savings inflow
Transfer to Savings                → savings inflow
Allocation to Savings              → savings inflow
Transfer to Spendable              → savings outflow
Allocation from Savings            → savings outflow
Expense from Savings               → savings outflow
```

The savings analytics endpoint can provide:

- total inflow
- total outflow
- net savings movement
- savings rate against deposits
- savings activity ledger
- movement-type analysis
- wallet/source analysis
- money-location analysis
- monthly summaries
- date filtering

No separate savings schema was required.

---

# 12. Phase 6 — Master Data and Configuration

Phase 6 expanded master-data lifecycle management.

Supported lifecycle operations include:

- Account create/edit/archive/reactivate
- Category create/edit/archive/reactivate
- Subcategory create/edit/archive/reactivate
- Item create/edit/archive/reactivate
- Owner create/edit/archive/reactivate
- MoneyLocation create/edit/archive/reactivate

## Archive instead of hard delete

Master data is generally deactivated instead of physically deleted.

This protects historical transactions from losing their foreign-key references.

Example:

```text
Category
   ├── Subcategory
   │      └── Item
   └── historical Transactions
```

Archiving a category also archives its subordinate subcategories/items where required, while historical transaction records remain readable.

A money location used by an active account cannot be archived.

Transaction-facing serializers reject inactive master-data selections.

---

# 13. Current Phase 7 — Browser/E2E Validation and Remediation

Phase 7 is the current remediation/validation phase.

The browser suite is implemented in:

```text
e2e/test_phase7.py
```

The suite covers:

```text
7.1 Dashboard smoke
7.2 Accounts: create → deposit → transfer → balance reconciliation
7.3 Expense workflow
7.4 Transaction search/edit/revert/delete
7.5 Categories/master data
7.6 Savings browser flow
7.7 SQL Playground
7.8 Reports
7.9 Responsive major pages
7.10 Settings page removed
```

## Current Phase 7.2 status

The login issue encountered during E2E execution has been resolved locally by using the configured E2E credentials.

The current failure happens later:

1. Login succeeds.
2. Accounts page loads.
3. Source wallet creation succeeds.
4. Destination wallet creation succeeds.
5. The browser enters a deposit amount of `500`.
6. The browser waits for `POST /api/accounts/<id>/deposit/` with HTTP 200.
7. The expected response does not arrive and Playwright times out after 30 seconds.

Therefore the current Phase 7.2 issue is a **deposit endpoint/application-flow problem**, not the original login problem.

The correct debugging strategy is to inspect the actual server-side exception/request behavior instead of weakening the E2E assertion.

## Settings removal

The current Phase 7 remediation also requires removal of the Settings page.

Important distinction:

- historical Phase 3 introduced `AppSetting` persistence and a Settings route
- the current Phase 7 requirement is to remove the Settings page
- removal must not reintroduce configuration duplication or break unrelated financial behavior
- whether the underlying `AppSetting` model should remain is a cleanup decision that must follow route/dependency tracing rather than being guessed

---

# 14. Financial Domain Model

The finance engine is centered on four related concepts:

```text
Account
  │
  ├── Allocation
  │     ├── Spendable
  │     └── Savings
  │
  ├── MoneyPool
  │     └── owner + location + allocation
  │
  └── Transaction ledger
```

These are different layers of the same financial truth.

## Account

Represents a wallet/payment source or financial container.

Examples conceptually:

- bank account
- UPI wallet
- cash wallet
- travel card
- change cash

Important fields include:

- UUID primary key
- name
- money location
- total balance
- currency
- active flag
- created/updated timestamps

`total_balance` is never supposed to become inconsistent with its allocations.

## Allocation

Represents the internal purpose split of an Account.

Allowed types:

```text
spendable
savings
```

Each account has at most one allocation of each type.

The database enforces:

```text
Unique(account, type)
```

## Owner

Represents the person associated with money ownership/source context.

Current household-oriented examples include:

- Me / current user context
- Appa
- Amma

Owner is separate from Account because an account/location can participate in ownership/source tracking without changing the physical wallet identity.

## MoneyLocation

Represents where the money physically/logically resides.

Types include:

```text
bank
cash
travel_card
change_cash
```

Examples from the family-money requirements include bank/cash locations such as TMB Bank, Appa Cash and Amma Cash.

## MoneyPool

MoneyPool is the source-level balance layer.

It tracks:

```text
Account
Owner
MoneyLocation
Allocation type
Current amount
```

The unique identity is account-scoped:

```text
Account + Owner + Location + Allocation Type
```

MoneyPool prevents the system from losing the source context of money while still allowing the Account and Allocation layers to provide simple wallet balances.

---

# 15. Transaction Ledger Model

`Transaction` is the audit/event history of money operations.

Important fields include:

- UUID id
- account
- owner
- money location
- allocation
- source pool
- category
- subcategory
- item
- variant
- meal
- transaction type
- amount
- metadata JSON
- created timestamp
- occurred timestamp
- related transaction

Transaction types currently include:

```text
deposit
expense
allocation
transfer
```

Every monetary movement should produce transaction history so reports, savings analytics and the SQL Playground can reconstruct what happened.

The transaction ledger is historical. It is not the same thing as the current `Allocation.balance`.

---

# 16. Master Data Model

The classification hierarchy is:

```text
Category
   ↓
SubCategory
   ↓
Item
   ↓
(optional) FoodProfile
```

## Category

Top-level classification.

Examples conceptually:

- Food
- Travel
- Bills
- Shopping

## SubCategory

Refines a category.

A subcategory belongs to exactly one category.

## Item

Represents a selectable master item under a category/subcategory.

Items can also be marked as custom.

The `variant` field on Transaction provides a way to record unexpected/custom detail without forcing every one-off variation into master data.

This is an important UI/business rule:

> **Do not create a new master item just because one expense has an unexpected variant.**

## FoodProfile

Food-specific metadata is attached one-to-one to an Item.

It can classify:

- food group
- health classification
- sugary status

## FoodEvent / FoodEventItem

Food-related transaction metadata can represent:

- meal type
- food vs drink
- multiple items
- quantity
- custom food names
- variants

---

# 17. Complete Database Relationship Map

Conceptually:

```text
Owner ───────────────┐
                     │
MoneyLocation ───────┼──→ MoneyPool ←── Account
                     │                 │
                     │                 ├──→ Allocation
                     │                 │       │
                     │                 │       └──→ Transaction
                     │                 │
                     └─────────────────┘

Category ──→ SubCategory ──→ Item
   │             │             │
   └─────────────┴─────────────┴──→ Transaction

Item ──→ FoodProfile

Transaction ──→ FoodEvent ──→ FoodEventItem ──→ Item

SavedQuery
    │
    └── SQL text

QueryExecutionLog
    └── execution history
```

The major financial relationship is:

```text
Account
  ├── allocations
  ├── money_pools
  └── transactions
```

This allows the application to answer three different questions:

1. **How much money is in the wallet now?** → Account/Allocation.
2. **Where/whose money is it?** → MoneyPool.
3. **What happened to it?** → Transaction.

---

# 18. Database Constraints and Integrity

The database uses constraints as a second line of defense after application logic.

Examples:

## Account

```text
account total_balance >= 0
```

## Allocation

```text
allocation balance >= 0
unique(account, type)
```

## MoneyPool

```text
current_amount >= 0
unique(account, owner, location, allocation_type)
```

## Transaction

```text
amount > 0
```

## SubCategory

```text
unique(category, name)
```

## Item

```text
unique(category, subcategory, name)
```

## FoodEventItem

```text
quantity > 0
item OR custom_name must be present
```

These constraints make invalid financial states harder to create even if a caller bypasses normal UI behavior.

---

# 19. Deposit Business Logic

Deposit endpoint:

```text
POST /api/accounts/<id>/deposit/
```

Example payload:

```json
{
  "amount": "1000",
  "allocate_to_savings": "300",
  "note": "salary"
}
```

Rules:

- amount must be positive
- savings allocation is optional
- savings allocation cannot exceed the deposit
- the remainder becomes spendable

For a deposit of 1000 with 300 to savings:

```text
Account total: +1000
Spendable:     +700
Savings:       +300
```

The endpoint also updates MoneyPool balances and writes Transaction rows.

The implementation uses a preparation/reconciliation layer to handle historical/legacy wallet states before applying new money.

This is particularly relevant to the current Phase 7.2 debugging because the browser test creates a new wallet and immediately deposits into it.

---

# 20. Expense Business Logic

An expense is a real outflow of money.

Conceptually:

```text
selected allocation -= expense amount
Account total       -= expense amount
```

The selected allocation must have sufficient funds.

Default behavior is to spend from Spendable unless the user explicitly selects Savings.

The transaction record stores the classification and source information so the expense can later be searched, reported, edited or reverted.

An expense is fundamentally different from an allocation transfer:

```text
Expense:
    money leaves the account

Allocation transfer:
    money stays in the account but changes bucket
```

---

# 21. Savings ↔ Spendable Transfer Logic

Transfer between allocations changes the internal split without changing the account total.

Example:

```text
Before:
Spendable = 700
Savings   = 300
Total     = 1000

Move 100 to Savings:

Spendable = 600
Savings   = 400
Total     = 1000
```

The backend checks:

1. source allocation exists
2. target allocation exists
3. source has enough balance
4. source MoneyPool has enough funds
5. source and target balances are updated atomically
6. MoneyPool values are updated
7. an allocation transaction is recorded
8. the account reconciles

---

# 22. Wallet-to-Wallet Transfer Logic

A wallet transfer is different from an allocation transfer.

Wallet transfer:

```text
Source Account total -= amount
Destination Account total += amount
```

The total across both accounts remains unchanged, assuming no external fee.

The transfer must preserve the accounting invariants of both accounts.

The current Accounts UI exposes:

- source wallet
- destination wallet
- owner
- amount

The backend performs the actual movement and ledger updates.

---

# 23. Legacy Balance Repair Logic

The current money engine contains defensive repair logic because the project evolved through multiple phases and historical/demo rows can predate the MoneyPool model.

`_repair_legacy_pool_balances()` handles a specific situation where:

```text
Account.total_balance > 0
Allocation totals = 0
MoneyPool totals = 0
```

For supported standard allocation wallets, that historical account-only balance is treated as spendable money and restored into the allocation/pool ledger before a new operation is applied.

The repair logic deliberately avoids blindly merging multiple owner pools because separate owner pools may represent legitimate ownership splits.

This repair behavior exists to preserve historical financial truth rather than to hide inconsistencies.

---

# 24. Atomicity and Concurrency

Every operation that changes money should be treated as a database transaction.

The pattern is:

```python
with transaction.atomic():
    account = Account.objects.select_for_update().get(...)
    ...
    update allocations
    update money pools
    create transaction ledger rows
    reconcile
```

Why this matters:

Without row locking, two concurrent requests could both read the same balance and overspend it.

Without atomicity, an operation could update the Account but fail before updating the Allocation or Transaction, producing a broken ledger.

The project therefore treats a monetary operation as one indivisible state transition.

---

# 25. API Architecture

The frontend communicates with Django using JSON HTTP requests.

General flow:

```text
Browser UI
   ↓ fetch()
Django URL router
   ↓
DRF/Django view
   ↓
Serializer validation
   ↓
transaction.atomic()
   ↓
Models / PostgreSQL
   ↓
Integrity checks
   ↓
JSON response
   ↓
Browser refreshes state
```

The browser is not the financial source of truth.

The server is responsible for validation and balance changes.

---

# 26. Core API Endpoints

## Accounts

```text
GET  /api/accounts/
POST /api/accounts/
GET  /api/accounts/<id>/
```

## Deposits

```text
POST /api/accounts/<id>/deposit/
```

## Allocation transfers

```text
POST /api/accounts/<id>/allocate/
POST /api/accounts/<id>/transfer-to-savings/
POST /api/accounts/<id>/transfer-to-spendable/
```

## Expenses

```text
POST /api/accounts/<id>/expense/
POST /api/expense/entry/
```

## Wallet transfer

```text
POST /api/wallet/transfer/
```

## Transactions

```text
GET  /api/accounts/<id>/transactions/
GET  /api/transactions/all/
GET  /api/transactions/filter-options/
POST /api/transactions/<id>/edit/
POST /api/transactions/<id>/revert/
```

## Master data

```text
GET/POST /api/categories/
GET/POST /api/subcategories/
GET/POST /api/items/
GET      /api/food-profiles/
GET      /api/owners/
GET      /api/money-locations/
GET      /api/money-pools/
```

## Reports

```text
GET /api/reports/
GET /api/reports/page/
GET /api/reports/data/
GET /api/accounts/<id>/summary/
GET /api/accounts/<id>/export.csv/
```

## Savings

```text
GET /api/savings/page/
GET /api/savings/analytics/
```

## SQL Playground

```text
GET  /api/sql/
POST /api/sql/execute/
POST /api/sql/execute-live/
GET  /api/sql/schema/
GET  /api/sql/schema-live/
GET  /api/sql/history/
GET  /api/sql/saved/
POST /api/sql/save/
```

The exact route set contains historical/alternate routes as well; cleanup work should distinguish canonical routes from legacy routes before removing anything.

---

# 27. API Validation Pattern

The API uses serializers to validate incoming data before entering financial operations.

For money values, JSON should use decimal strings rather than floating-point numbers where possible.

Example:

```json
{"amount": "500.00"}
```

This avoids binary floating-point rounding problems.

Validation errors are returned as JSON with HTTP 400 where appropriate.

Authentication errors are returned as HTTP 401 for protected API endpoints.

---

# 28. Accounts Page Architecture

The Accounts page is one of the most important operational pages.

It contains four major UI areas:

1. **Create wallet/account**
2. **Fund a wallet**
3. **Savings & Spendable allocation control**
4. **Wallet-to-wallet transfer**
5. **Wallet balances**

The current template is:

```text
pg_expense/templates/accounts.html
```

The page uses browser JavaScript and Fetch API calls.

### Create wallet

The UI submits:

```text
POST /api/wallet/accounts/create/
```

with:

- name
- currency
- location type
- location name

### Deposit

The UI calls:

```text
POST /api/accounts/<id>/deposit/
```

with the entered amount and an explicit savings allocation value.

### Allocation

The UI calls:

```text
POST /api/accounts/<id>/transfer-to-savings/
POST /api/accounts/<id>/transfer-to-spendable/
```

### Wallet transfer

The UI calls:

```text
POST /api/wallet/transfer/
```

The page reloads account data after successful mutations so displayed balances come from the server rather than local arithmetic.

---

# 29. Current Phase 7.2 Browser Workflow

The E2E test intentionally exercises a realistic browser sequence:

```text
Login
  ↓
Open Accounts page
  ↓
Create source wallet
  ↓
Create destination wallet
  ↓
Deposit 500 into source
  ↓
Verify persisted balance
  ↓
Transfer money
  ↓
Verify source/destination balances
  ↓
Reconcile financial state
```

This is more valuable than testing only an isolated API because it verifies:

- authentication
- page routing
- DOM controls
- JavaScript request wiring
- API routing
- backend business logic
- database persistence
- UI refresh
- final financial state

The current failure is in the deposit step after wallet creation, so investigation must trace the entire browser-to-database path.

---

# 30. SQL Playground Architecture

The SQL Playground is a learning environment over the same PostgreSQL database.

The browser never connects directly to PostgreSQL.

Instead:

```text
SQL editor
   ↓
POST /api/sql/execute/
   ↓
Django secure SQL executor
   ↓
validation
   ↓
PostgreSQL READ ONLY transaction
   ↓
result set
   ↓
JSON
   ↓
result table in browser
```

## Read-only policy

The intended safe query class includes read-only statements such as:

```text
SELECT
WITH
SHOW
DESCRIBE
EXPLAIN
VALUES
```

Destructive/write operations such as:

```text
INSERT
UPDATE
DELETE
DROP
CREATE
ALTER
TRUNCATE
COPY
VACUUM
GRANT
REVOKE
```

are blocked.

The important security improvement is that PostgreSQL itself is placed into a read-only transaction for the query, so safety is not dependent only on a Python keyword filter.

## Resource limits

The SQL Playground also has:

- statement timeout
- result row limit
- query history
- saved query validation

The active implementation records history after the protected read-only transaction completes.

---

# 31. SQL Playground UI Components

The SQL page is designed as a mini database workstation rather than just a text box.

The intended UI contains:

## SQL editor

A user writes a query and executes it.

## Results panel

Displays:

- column names
- rows
- row count
- execution time
- errors

## Schema explorer

Displays live PostgreSQL tables and columns.

## Relationship/database explanation

Shows how important application tables relate.

## Saved queries

Users can save reusable read-only SQL statements.

## Query history

Previously executed queries can be inspected.

## Frequent/useful query area

Useful examples help users learn SQL against the actual application schema.

---

# 32. Reporting Architecture

Reports are derived from financial records rather than maintaining separate duplicated report tables.

The reporting layer can calculate:

- total income/deposits
- total expenses
- net balance
- savings amount/movement
- wallet breakdown
- category spending
- period trends

This follows the same source-of-truth principle:

```text
Transactions + current account state
                ↓
            Reporting
```

Reports should not become another balance ledger.

---

# 33. Savings Reporting Architecture

Savings reporting is transaction-derived.

This prevents a common accounting error where both:

- current Savings allocation
- separate savings ledger

are counted as independent money.

The analytics layer classifies transaction movements once and produces period summaries.

The savings rate is based on savings movement relative to the deposit base for the selected period.

---

# 34. Frontend Security and Data Rendering

The project uses a centralized `escapeHtml()` helper in the active templates for API-derived data inserted into HTML strings.

Dynamic values such as:

- account names
- wallet locations
- owners
- categories
- subcategories
- items
- transactions
- SQL result data
- saved query text
- query history

must not be inserted as uncontrolled raw HTML.

For status/preview areas where possible, `textContent` is used.

Dynamic IDs/UUIDs inserted into URLs are encoded using `encodeURIComponent()`.

CSRF tokens are sent with browser POST requests.

---

# 35. Authentication Flow

The browser authentication lifecycle is:

```text
GET /login/
    ↓
username + password
    ↓
Django LoginView
    ↓
session cookie
    ↓
application page/API access
```

The Phase 7 E2E tests use environment variables:

```text
E2E_USERNAME
E2E_PASSWORD
```

The credentials are not stored in source code.

The browser test first verifies that successful login reaches the expected dashboard route before executing the individual Phase 7 workflow.

---

# 36. Current Test Strategy

The project uses multiple levels of verification.

## Backend unit/integration tests

Run:

```text
python manage.py test
```

These verify business logic, database behavior, security and regressions.

The latest local run reported during the current work had:

```text
63 tests
63 passed
```

## Targeted browser test

Current Phase 7.2 command:

```text
pytest e2e/test_phase7.py::test_7_2_accounts_create_deposit_transfer_and_balance -v -s
```

## Full browser suite

```text
pytest e2e/test_phase7.py -v -s
```

The suite contains 17 collected browser tests in the current file, including parameterized responsive checks.

## Important testing principle

A test failure is evidence of a mismatch somewhere in the actual system.

The preferred debugging order is:

```text
Test failure
   ↓
Reproduce
   ↓
Inspect actual request/response
   ↓
Inspect server traceback
   ↓
Trace business logic
   ↓
Find root cause
   ↓
Make smallest correct fix
   ↓
Run targeted test
   ↓
Run full regression suite
```

Do not modify tests merely to hide application failures.

---

# 37. Phase 7 Settings Removal Rule

The current remediation specifically includes removal of the Settings page.

Historically, Phase 3 created a persisted Settings system, including `AppSetting` and a `/api/settings/` route.

The current Phase 7 E2E requirement is:

```text
test_7_10_settings_page_removed
```

The correct cleanup sequence is:

1. identify all Settings routes
2. identify template references
3. identify sidebar/navigation references
4. identify API consumers
5. identify tests
6. determine whether `AppSetting` is still required elsewhere
7. remove the Settings page safely
8. update navigation
9. verify no broken links remain
10. run Phase 7 tests

Do not remove the model blindly if it is still required by unrelated application logic.

---

# 38. Why the Architecture Has Both Account and MoneyPool

This is one of the most important architectural decisions in the project.

A simple expense tracker could use:

```text
Account → balance
```

but the actual family-money requirements need to know more:

```text
Who owns the money?
Where is it held?
Which allocation is it assigned to?
Which account contains it?
```

Therefore:

```text
Account
   ↓
MoneyPool
   ↓
Owner + Location + Allocation
```

Account gives the wallet-level view.

Allocation gives the spendable/savings view.

MoneyPool gives the ownership/source view.

Transaction gives the historical event view.

This layered design allows the UI to stay simple while preserving traceability underneath.

---

# 39. Source-of-Truth Rules

The project follows these rules:

## Current balances

```text
Account / Allocation / MoneyPool
```

must reconcile.

## Historical events

```text
Transaction
```
is the audit ledger.

## Savings analytics

```text
Transaction
```
is the historical source used to classify savings movements.

## Reports

Reports are computed from existing financial records.

## SQL Playground

Queries the same PostgreSQL database.

There should not be multiple independent copies of the financial truth.

---

# 40. Common Financial Scenarios

## Scenario A — Deposit entirely spendable

```text
Initial:
Total = 0
Spendable = 0
Savings = 0

Deposit = 1000

Final:
Total = 1000
Spendable = 1000
Savings = 0
```

## Scenario B — Deposit with savings allocation

```text
Deposit = 1000
Savings allocation = 300

Final:
Total = 1000
Spendable = 700
Savings = 300
```

## Scenario C — Move spendable to savings

```text
Before:
Total = 1000
Spendable = 700
Savings = 300

Move = 200

After:
Total = 1000
Spendable = 500
Savings = 500
```

## Scenario D — Expense from spendable

```text
Before:
Total = 1000
Spendable = 700
Savings = 300

Expense = 150

After:
Total = 850
Spendable = 550
Savings = 300
```

## Scenario E — Expense from savings

```text
Before:
Total = 1000
Spendable = 700
Savings = 300

Expense from savings = 100

After:
Total = 900
Spendable = 700
Savings = 200
```

## Scenario F — Wallet transfer

```text
Wallet A = 1000
Wallet B = 200

Transfer 300 A → B

Wallet A = 700
Wallet B = 500
```

The aggregate money across both wallets remains 1200.

---

# 41. Master Data Business Rules

Master data is configuration/reference data rather than financial events.

Therefore:

- categories can be archived
- subcategories can be archived
- items can be archived
- owners can be archived
- money locations can be archived where safe

But historical transaction rows should remain valid.

This is why archive/reactivate is preferred over hard delete.

Transaction selectors must reject inactive values for new transactions.

---

# 42. Error Handling Philosophy

API errors should be explicit and machine-readable.

Examples:

```json
{
  "detail": "Insufficient funds in spendable allocation."
}
```

or:

```json
{
  "detail": "Savings allocation cannot exceed deposit amount."
}
```

The frontend displays these errors rather than silently pretending an operation succeeded.

For browser E2E testing, an HTTP 500 or unexpected response is considered a real application failure and must be investigated.

---

# 43. Current Deposit Endpoint Debugging Context

The current deposit implementation is in:

```text
wallet/account_money_views.py
```

The endpoint performs approximately this sequence:

```text
Validate DepositSerializer
        ↓
Validate savings <= deposit
        ↓
Lock Account
        ↓
Ensure Spendable/Savings allocations
        ↓
Resolve Owner + MoneyLocation context
        ↓
Prepare/reconcile legacy money context
        ↓
Reload allocations after repair
        ↓
Calculate spendable portion
        ↓
Increase Account.total_balance
        ↓
Increase Spendable
        ↓
Increase Savings if applicable
        ↓
Update MoneyPool(s)
        ↓
Create Deposit Transaction row(s)
        ↓
Refresh state
        ↓
Assert reconciliation
        ↓
Return AccountSerializer JSON
```

The current Phase 7.2 failure occurs somewhere along this path for a newly-created browser-test wallet.

The correct next action is to inspect the actual server-side behavior and traceback.

---

# 44. Current Accounts UI Deposit Context

The current Accounts template renders a deposit card for each account.

Conceptually:

```html
<input class="deposit" ...>
<button class="add-money">Add</button>
```

The JavaScript performs:

```text
read amount
   ↓
POST /api/accounts/<id>/deposit/
   ↓
read JSON response
   ↓
reload accounts
```

The current browser E2E test waits for HTTP 200 on that exact request.

Therefore, if the request never produces the expected response, the debugging target is the actual network/backend behavior rather than the test's selector.

---

# 45. Legacy and Canonical Implementations

The project has evolved through several phases and therefore contains some older implementation paths alongside newer canonical flows.

Examples include modules such as:

- `views.py`
- `feature_views.py`
- `complete_flow_views.py`
- `complete_flow_fixes.py`
- `phase4_views.py`
- `account_money_views.py`
- `transaction_page.py`

The remediation strategy is not to delete files simply because newer files exist.

Before changing a route or implementation:

1. identify URL mapping
2. identify frontend consumers
3. identify tests
4. identify shared helpers
5. identify migrations/data dependencies
6. choose the canonical implementation
7. only then remove or deprecate the old path

---

# 46. Why Historical Migrations Are Preserved

Django migrations are the historical record of database evolution.

They should not be rewritten just to make the current model look cleaner.

A clean project can have many migrations because they describe how the schema reached its current state.

The preferred verification is:

```text
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

The second command verifies that the model state and migrations remain aligned without silently generating new migration files.

---

# 47. Recommended Development Workflow

For any future feature or fix:

## Step 1 — Understand the requirement

Write down the business rule before touching code.

## Step 2 — Trace the existing architecture

Find:

- model
- serializer
- view
- URL
- template
- JavaScript
- tests

## Step 3 — Reproduce

Run the smallest relevant test.

## Step 4 — Inspect actual state

Use the database, request/response and traceback rather than assumptions.

## Step 5 — Implement the smallest change

Do not redesign unrelated modules.

## Step 6 — Run targeted tests

Confirm the immediate behavior.

## Step 7 — Run regression tests

Confirm financial invariants remain intact.

## Step 8 — Run browser tests where UI/API integration changed

Confirm the actual user workflow.

## Step 9 — Document the decision

Update this file and the relevant phase/API documentation.

---

# 48. Local Commands

Activate the virtual environment:

```powershell
. .\.venv\Scripts\Activate.ps1
```

Run backend tests:

```powershell
python manage.py test
```

Run migrations:

```powershell
python manage.py migrate
```

Check migration consistency:

```powershell
python manage.py makemigrations --check --dry-run
```

Run the development server:

```powershell
python manage.py runserver
```

Run the current Phase 7.2 browser test:

```powershell
pytest e2e/test_phase7.py::test_7_2_accounts_create_deposit_transfer_and_balance -v -s
```

Run the complete Phase 7 browser suite:

```powershell
pytest e2e/test_phase7.py -v -s
```

Inspect Git state:

```powershell
git status
git branch --show-current
git diff
```

---

# 49. Environment and Secrets

The local environment uses `.env` for values such as:

- Django secret configuration
- PostgreSQL connection details
- database credentials
- SQL Playground configuration where applicable

`.env` must remain outside Git.

Never put real credentials in:

- source code
- documentation
- E2E tests
- Git commits
- Gemini instructions

E2E credentials are supplied through environment variables at runtime.

---

# 50. Production Direction

Production hardening remains a separate concern from the local/demo environment.

The intended production improvements include:

- DEBUG disabled
- explicit secret configuration
- restricted ALLOWED_HOSTS
- HTTPS
- secure cookies
- production database credentials
- least-privilege PostgreSQL roles
- stronger deployment-level SQL isolation
- appropriate API authentication/authorization
- backups and operational monitoring

The current application is being developed and validated as a local/demo product first.

---

# 51. Future Multi-User Architecture

The current application is intentionally a single private household workspace.

If the product becomes a real multi-user SaaS application, the financial model should explicitly add user ownership rather than relying on assumptions.

A future design could introduce:

```text
Django User
    ↓
Workspace / Household
    ↓
Accounts
    ↓
Allocations / MoneyPools / Transactions
```

Authorization would then need to be enforced at the queryset/object level for every financial resource.

This is deliberately not silently implemented in the current model.

---

# 52. Architecture Summary

The complete architecture can be understood as five layers.

## Layer 1 — Presentation

```text
Django templates + CSS + JavaScript
```

Responsible for forms, navigation, tables, filters, SQL editor and user feedback.

## Layer 2 — HTTP/API

```text
Django URLs + DRF views + serializers
```

Responsible for authentication, validation and request/response contracts.

## Layer 3 — Business logic

```text
transactions
allocations
money pools
financial integrity helpers
reporting
savings classification
SQL security
```

Responsible for financial truth and rules.

## Layer 4 — Persistence

```text
Django ORM
   ↓
PostgreSQL
```

Responsible for durable state, constraints and atomic transactions.

## Layer 5 — Verification

```text
Django tests
pytest
Playwright E2E
```

Responsible for proving that each layer works together.

---

# 53. End-to-End Example: From User Action to Database

Suppose the user enters:

```text
Deposit ₹500 into Wallet A
```

The complete flow is:

```text
User clicks Add
        ↓
accounts.html JavaScript reads 500
        ↓
Fetch POST /api/accounts/<id>/deposit/
        ↓
Django URL resolves deposit_funds_fixed
        ↓
DepositSerializer validates amount
        ↓
Account row is locked
        ↓
Allocation/pool context is prepared
        ↓
Account total increases by 500
        ↓
Spendable increases by 500
        ↓
MoneyPool increases by 500
        ↓
Transaction(type=deposit, amount=500) created
        ↓
Reconciliation check
        ↓
AccountSerializer returns JSON
        ↓
Browser reloads /api/accounts/
        ↓
UI displays the persisted balance
```

This example illustrates why the current Phase 7.2 failure is important: it tests the entire stack, not just one function.

---

# 54. What Must Never Be Broken

The following are core project invariants and must survive future changes:

1. `Spendable + Savings = Account.total_balance` for accounts using the allocation model.
2. MoneyPool totals must reconcile with the account/allocation state.
3. Financial operations must be atomic.
4. Balance-changing rows must be protected against concurrent modification.
5. Expenses cannot exceed the selected available allocation.
6. Allocation transfers do not change the account total.
7. Wallet transfers move money between accounts rather than creating money.
8. Every monetary movement remains auditable through Transaction records.
9. Savings analytics must not double-count money.
10. SQL Playground must remain read-only.
11. Historical transaction references must remain readable when master data is archived.
12. Tests must not be weakened to hide broken business behavior.

---

# 55. Current Project State

At the point this document was expanded:

## Completed/implemented foundation

- Django + PostgreSQL application
- wallet/account model
- spendable/savings allocation model
- owner/location/source tracking
- MoneyPool accounting layer
- transaction ledger
- deposit flow
- expense flow
- allocation transfer flow
- wallet transfer flow
- category/subcategory/item hierarchy
- food metadata/event support
- dashboard
- transaction ledger/search/filtering
- reports
- savings analytics
- SQL Playground
- live PostgreSQL schema explorer
- saved queries
- query history
- session authentication
- SQL read-only enforcement
- browser/E2E Phase 7 suite

## Current remediation

- Phase 7 browser workflow verification
- Phase 7.2 Accounts workflow fix
- Settings page removal
- broader Phase 7 E2E validation

## Latest local verification context

The latest backend test run reported during the current development session completed successfully with 63 tests passing.

The Phase 7 browser suite initially skipped because E2E credentials were placeholders. After configuring the E2E credentials, login succeeded and Phase 7.2 progressed to the deposit step.

The current Phase 7.2 failure is the deposit request not producing the expected HTTP 200 response within Playwright's timeout.

This is the immediate engineering problem to solve.

---

# 56. How Gemini CLI Should Work With This Project

`GEMINI.MD` is being used as the repository-level instruction file for Gemini CLI.

Gemini should:

1. read this documentation before making broad changes
2. inspect actual source code before assuming behavior
3. reproduce failures
4. identify root causes
5. make minimal changes
6. preserve financial invariants
7. never weaken tests just to get green output
8. run targeted tests first
9. run regression tests afterward
10. avoid destructive Git commands unless explicitly instructed

For Phase 7.2 specifically, Gemini should investigate the deposit request and server-side traceback before editing the deposit implementation.

---

# 57. Documentation Map

Use the documentation files for different levels of detail:

| Document | Purpose |
|---|---|
| `working.md` | Complete system working/architecture map |
| `API_DOCS.md` | API contracts and endpoint behavior |
| `NOTES.md` | Compact project notes and development rules |
| `plan.md` | Long-form project plan and requirements history |
| `PHASE_0_BASELINE.md` | Baseline and remediation safety rules |
| `PHASE_1_SECURITY.md` | Authentication/security implementation |
| `PHASE_2_FINANCIAL_INTEGRITY.md` | Financial invariants and integrity hardening |
| `PHASE_3_UI_COMPLETION.md` | Core UI completion |
| `PHASE_4_SEARCH_SQL.md` | Search/filtering and SQL Playground hardening |
| `PHASE_5_SAVINGS.md` | Savings analytics design |
| `PHASE_6_MASTER_DATA.md` | Master-data lifecycle/configuration |
| `e2e/test_phase7.py` | Browser acceptance workflows |

---

# 58. Final Mental Model

If the entire project has to be remembered in one diagram, use this:

```text
                         PG EXPENSE
                             │
             ┌───────────────┴────────────────┐
             │                                │
        Browser UI                        SQL Playground
             │                                │
             ↓                                ↓
      Django URLs / APIs              Secure SQL Executor
             │                                │
             └───────────────┬────────────────┘
                             ↓
                     BUSINESS LOGIC
                             │
          ┌──────────────────┼───────────────────┐
          │                  │                   │
       Accounts          Transactions        Master Data
          │                  │                   │
          ├── Allocation     ├── Deposit         ├── Category
          │   ├─ Spendable   ├── Expense         ├── SubCategory
          │   └─ Savings     ├── Allocation      ├── Item
          │                  └── Transfer        ├── Owner
          │                                      └── Location
          │
          └── MoneyPool
              └── Owner + Location + Allocation
                             │
                             ↓
                       PostgreSQL
                             │
                             ↓
                    Financial Integrity
                             │
                ┌────────────┴────────────┐
                │                         │
             Reports                  Savings Analytics
                │                         │
                └────────────┬────────────┘
                             ↓
                         Auditability
                             │
                         Tests / E2E
```

The central principle remains:

> **One financial truth, multiple useful views.**

Account shows the wallet total. Allocation shows spendable versus savings. MoneyPool explains ownership/source. Transaction explains history. Reports and savings analytics derive information from those records. The SQL Playground exposes the same PostgreSQL data for learning and analysis.

That separation is the foundation that future fixes must preserve.
