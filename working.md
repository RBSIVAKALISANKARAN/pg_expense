# How the System Works

This project is a personal finance management app that combines:

- wallet operations
- allocation tracking
- transaction recording
- category and item tagging
- SQL playground exploration
- dashboard and reporting interface

The whole system is designed around one central rule:

- spendable + savings = total balance

This means savings is treated as a reserved part of the same money, not as a second copy of the same amount.

1. Core financial model

The project uses a few primary database entities:

- Account: the wallet or source of money
- Allocation: the split of the account into spendable and savings
- Transaction: every money change or movement
- Category: classification bucket such as Food, Travel, Bills
- Item: subcategory under a category
- SavedQuery and QueryExecutionLog: SQL practice and query history

Account model
- holds name, currency, total_balance, created_at, updated_at
- each account is a financial container

Allocation model
- two allowed types:
  - spendable
  - savings
- each allocation belongs to an account
- each allocation stores its own balance

Example:
- account = GPay
- spendable balance = 700
- savings balance = 300
- total balance = 1000

This is the core accounting logic built into the app.

2. How money is stored

When a user creates an account, the app creates two allocation rows automatically:

- spendable
- savings

Each is stored in the database with its own balance. The app does not duplicate the value incorrectly.

When a deposit happens:
- the total account balance goes up
- the deposit can be split between spendable and savings based on `allocate_to_savings`

Example:
- deposit 1000
- allocate_to_savings = 300
- spendable becomes 700
- savings becomes 300
- total is still 1000

When expense happens:
- the chosen bucket loses money
- total balance also decreases
- expenses can be charged directly to spendable or savings

When a transfer happens:
- one bucket loses money
- the other gains money
- total balance does not change

3. Money flow logic

The user experience is intentionally direct:

- deposit adds money to the account
- default spendable is the normal spending bucket
- savings is optional but tracked separately
- transfers move the split without changing the total balance
- expenses consume the balance from the chosen bucket

This matches the requirement where a user may have:

- 1000 in GPay
- 300 assigned to savings
- 700 assigned to spendable

Then expenses are deducted from spendable, unless the user deliberately chooses savings.

4. Database storage details

The application uses PostgreSQL.

Tables include:

- wallet_account
- wallet_allocation
- wallet_transaction
- wallet_category
- wallet_item
- wallet_savedquery
- wallet_queryexecutionlog

Relationships:
- Account has many allocations
- Account has many transactions
- Allocation has many transactions
- Category has many items
- Item and Category can be linked to transactions for classification

The app stores the money as Decimal with 2 decimal precision so values remain stable and accurate.

5. How frontend data is stored

A typical front-end flow is:

1. User enters data in the dashboard or account page
2. Browser sends JSON to Django API
3. Django view validates the payload
4. Database transaction updates the relevant model rows
5. Account and allocation totals are refreshed
6. UI is reloaded with fresh values

Examples:

- Create account form → POST /api/accounts/
- Deposit form → POST /api/accounts/<id>/deposit/
- Expense form → POST /api/accounts/<id>/expense/
- Transfer form → POST /api/accounts/<id>/transfer-to-savings/

Transaction records capture the movement so the system has an audit trail of every monetary event.

6. How the SQL playground works

The SQL playground is designed as a read-only query environment for a real PostgreSQL database.

Security approach:
- the browser never connects directly to PostgreSQL
- all SQL goes through Django
- the backend validates the query
- destructive commands are blocked
- only read-only statements are allowed for safety

Allowed query patterns:
- SELECT
- WITH
- SHOW
- DESCRIBE
- EXPLAIN
- VALUES

Blocked patterns:
- DROP
- DELETE
- UPDATE
- INSERT
- CREATE
- ALTER
- TRUNCATE
- COPY
- VACUUM
- REVOKE
- GRANT

The result is shown in a dynamic table in the browser with:
- columns
- rows
- row count
- execution time

There are also:
- schema panel
- saved queries panel
- history panel
- frequent queries section

These help the user understand the database structure before writing SQL.

7. How the SQL explorer explains the database

The schema side panel reads the PostgreSQL information schema and shows:

- public tables
- table names
- column names

This helps the user know what can be queried.

The connections panel explains the main relationships:

- account → allocations
- account → transactions
- category → items
- allocation → transactions

The data flow panel shows the path from frontend form submission to database storage, explaining how the app works end-to-end.

8. How reporting works

The reports page reads account and transaction data and computes:

- total income
- total expenses
- net balance
- savings rate
- wallet breakdown
- category spend summary

It reads the real transaction records and calculates aggregates without storing duplicate report tables.

9. App user flow

Typical user journey:

- create wallet account
- deposit salary
- choose allocation split
- spend from spendable
- transfer some funds to savings
- review transaction history
- open SQL playground and analyze the database
- review period reports and category trends

10. Design principles in this project

- keep total value consistent
- maintain financial truth in allocation and total balance
- store each transaction as an audit log
- avoid silent duplication of money
- keep the database readable for learning and reporting
- make the UI feel like a real product while keeping logic clean and maintainable

11. Important implementation decisions

- Money uses Decimal values for financial safety
- Balance changes happen inside database transactions
- `select_for_update()` is used on balance-changing actions
- `F()` expressions keep arithmetic atomic and predictable
- SQL playground is intentionally safe and read-only

12. In short

The project is not just a dummy demo. It is a working personal finance system with:

- wallet accounting
- balance splitting
- spending logic
- transaction tracking
- SQL exploration
- reporting
- app-style UI

It is structured so the business logic remains truthful and explainable, and the database remains the single source of reporting truth.
