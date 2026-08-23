# Expense Tracking API Documentation

## Overview
This project exposes a lightweight JSON API for the personal finance app built around the rule:

- spendable + savings = total balance
- savings is an earmarked portion of the same money
- expenses default to spendable unless explicitly set to savings
- transfers between spendable and savings do not change total balance

Base URL:
- Local: http://127.0.0.1:8000/api/

Authentication:
- Current local development setup: open endpoints, no auth required
- Production recommendation: add JWT or token auth at API layer

## Core financial rules
- Every account starts with two allocations: spendable and savings
- A deposit increases total_balance
- A deposit can optionally split between allocations using allocate_to_savings
- An expense reduces the selected allocation and total_balance
- A transfer from spendable to savings or vice versa changes only the allocation split, not the total

## Accounts

### GET /api/accounts/
Lists all accounts with their allocations.

Example response:
[
  {
    "id": "<uuid>",
    "name": "GPay",
    "currency": "INR",
    "total_balance": "1000.00",
    "allocations": [
      {"id": "<uuid>", "type": "spendable", "balance": "700.00"},
      {"id": "<uuid>", "type": "savings", "balance": "300.00"}
    ]
  }
]

### POST /api/accounts/
Creates a new account. The server creates spendable and savings rows automatically.

Payload:
{
  "name": "GPay",
  "currency": "INR"
}

Response: 201 Created

### GET /api/accounts/<id>/
Returns a single account with allocations and latest numeric state.

## Deposits

### POST /api/accounts/<id>/deposit/
Adds funds to an account.

Payload:
{
  "amount": "1000",
  "allocate_to_savings": "300",
  "note": "salary"
}

Rules:
- amount must be greater than zero
- allocate_to_savings is optional
- allocate_to_savings cannot exceed amount
- the remainder goes to spendable by default

Result:
- total_balance increases by the deposit amount
- spendable + savings remains equal to total_balance

## Expenses

### POST /api/accounts/<id>/expense/
Creates a spending record.

Payload:
{
  "amount": "200",
  "allocation": "spendable",
  "merchant": "Cafe",
  "note": "coffee"
}

Rules:
- amount must be positive
- allocation must be spendable or savings
- the selected allocation must have enough balance
- total_balance reduces by the spent amount

## Transfers between allocations

### POST /api/accounts/<id>/transfer-to-savings/
Moves funds from spendable to savings.

Payload:
{
  "amount": "100"
}

### POST /api/accounts/<id>/transfer-to-spendable/
Moves funds from savings to spendable.

Payload:
{
  "amount": "100"
}

Rules:
- source allocation must have enough balance
- total_balance does not change

## Allocation direct move

### POST /api/accounts/<id>/allocate/
Allows direct movement between allocation buckets.

Payload:
{
  "from_type": "spendable",
  "to_type": "savings",
  "amount": "100"
}

## Transactions

### GET /api/accounts/<id>/transactions/
Returns real transaction records for the account, newest first.

Example item:
{
  "id": "<uuid>",
  "account": "<uuid>",
  "allocation": "<uuid>",
  "allocation_type": "spendable",
  "type": "expense",
  "amount": "200.00",
  "metadata": {"merchant": "Cafe"},
  "created_at": "2025-01-01T10:00:00Z"
}

## Categories and items

### GET /api/categories/
List categories.

### POST /api/categories/
Create a category.

Payload:
{
  "name": "Food",
  "description": "Meals and groceries"
}

### GET /api/items/
List items.

### POST /api/items/
Create an item linked to a category.

Payload:
{
  "category": "<category-id>",
  "name": "Lunch"
}

## Reports

### GET /api/reports/
Returns aggregated summary data for the app.

Typical fields:
- total_income
- total_expenses
- net_balance
- savings_amount
- category_breakdown
- monthly_trend

## SQL playground

### POST /api/sql/execute/
Executes a read-only SQL query against the real PostgreSQL database.

Payload:
{
  "sql": "SELECT * FROM wallet_account LIMIT 10;"
}

Rules:
- browser never connects directly to PostgreSQL
- Django validates the query before execution
- destructive statements are blocked
- only read-only statements are permitted

Examples of allowed statements:
- SELECT
- WITH
- EXPLAIN
- SHOW
- DESCRIBE
- VALUES

Examples of blocked statements:
- DELETE
- UPDATE
- INSERT
- DROP
- CREATE
- ALTER
- TRUNCATE
- VACUUM

### GET /api/sql/schema/
Returns table and column metadata from PostgreSQL.

### GET /api/sql/history/
Returns recent executed queries.

### POST /api/sql/save/
Saves a named SQL query.

### GET /api/sql/saved/
Lists saved queries.

## Error handling
The API returns 400 Bad Request with a JSON error message when validation fails.

Example:
{
  "detail": "Insufficient funds in spendable allocation."
}

## Data and consistency rules
- Money is stored as Decimal with 2 decimal precision
- All balance-changing endpoints run inside database transactions
- The backend uses row locking and atomic arithmetic to reduce race conditions
- Every money movement is recorded as a transaction row for auditability

## Typical flow
1. User creates an account
2. The app creates spendable + savings allocations
3. User deposits money and optionally allocates part to savings
4. User spends from spendable by default, or from savings if chosen explicitly
5. Every deposit, expense, transfer, and allocation movement is saved as transaction data
6. Dashboard and reports read from the same underlying Postgres tables
7. SQL playground queries the same data for learning and analysis

## Current project status
This API is already wired to the real finance product flow and the SQL playground is operating as a read-only PostgreSQL learning environment.

## Future improvements
- JWT or token authentication
- Pagination for transactions and reports
- CSV export
- Chart-based analytics
- Permission scoping for multi-user production usage

