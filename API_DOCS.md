Expense Tracking - API Documentation

Base URL
- Local development: http://127.0.0.1:8000/api/

Authentication
- Current implementation: no auth required for local dev (open endpoints).
- For multi-user or production, add token/JWT auth (DRF) and require Authorization headers.

Resources and Endpoints

1) Accounts
- GET /api/accounts/
  - Description: List all accounts with allocations
  - Response: 200 OK
  - Example response body:
    [
      {
        "id": "<uuid>",
        "name": "GPay",
        "currency": "INR",
        "total_balance": "800.00",
        "allocations": [
           {"id": "<uuid>", "type": "spendable", "balance": "500.00"},
           {"id": "<uuid>", "type": "savings", "balance": "300.00"}
        ]
      }
    ]

- POST /api/accounts/
  - Description: Create an account. The server creates spendable and savings allocations (0.00) automatically.
  - Body: {"name":"AccountName", "currency":"INR"}
  - Response: 201 Created (account representation)
  - PowerShell example:
      Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/accounts/' -ContentType 'application/json' -Body '{"name":"MyBank","currency":"INR"}'

- GET /api/accounts/{id}/
  - Description: Get account details including allocations

2) Deposits
- POST /api/accounts/{id}/deposit/
  - Description: Deposit money into the account. By default the deposit goes to spendable unless allocate_to_savings is set.
  - Body: {"amount":"1000","allocate_to_savings":"300","note":"initial deposit"}
    - allocate_to_savings is optional; if provided it must be <= amount.
  - Response: 200 OK (updated account)
  - Behavior: account.total_balance increases by amount; allocations updated so spendable + savings == total_balance
  - PowerShell example:
      Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/accounts/{id}/deposit/' -ContentType 'application/json' -Body '{"amount":"2000","allocate_to_savings":"500","note":"initial deposit"}'

3) Allocation Transfers (move between buckets)
- POST /api/accounts/{id}/allocate/
  - Body: {"from_type":"spendable","to_type":"savings","amount":"100"}
  - Behavior: subtract amount from source allocation and add to target (no change to total_balance). Prevents negative source.

4) Expenses (spending)
- POST /api/accounts/{id}/expense/
  - Description: Create an expense against an allocation. Default allocation: spendable.
  - Body: {"amount":"200","allocation":"spendable","merchant":"Cafe","note":"coffee"}
  - Behavior: deduct amount from allocation.balance and from account.total_balance. Prevent overspend (returns 400)

5) Transfers between allocations
- POST /api/accounts/{id}/transfer-to-savings/
  - Body: {"amount":"100"}
  - Moves funds from spendable -> savings (allocations only)

- POST /api/accounts/{id}/transfer-to-spendable/
  - Body: {"amount":"100"}
  - Moves funds from savings -> spendable

6) Transactions
- GET /api/accounts/{id}/transactions/
  - Description: List transaction records for an account in reverse chronological order.
  - Each Transaction includes: id, account (uuid), allocation (uuid or null), allocation_type (spendable/savings), type (deposit/expense/allocation/transfer), amount, metadata (object), created_at

Error Handling
- All endpoints return 400 Bad Request and a JSON message for validation errors (e.g., insufficient funds, invalid amounts).
- Example insufficient funds:
  {"detail": "Insufficient funds in spendable allocation."}

Concurrency & Consistency
- All balance-modifying endpoints use database transactions and select_for_update() to lock rows during updates.
- F() expressions are used for atomic arithmetic and objects are refreshed after save to resolve computed values.

Data Types
- Money is stored as Decimal with 2 decimal places (max_digits=12, decimal_places=2). Avoid using float in client code.

Testing the API (examples)
- Create account (PowerShell):
  Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/accounts/' -ContentType 'application/json' -Body '{"name":"MyBank","currency":"INR"}'

- Deposit (PowerShell):
  Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/accounts/{id}/deposit/' -ContentType 'application/json' -Body '{"amount":"2000","allocate_to_savings":"500","note":"initial deposit"}'

- Expense (PowerShell):
  Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/accounts/{id}/expense/' -ContentType 'application/json' -Body '{"amount":"200","allocation":"spendable","merchant":"Cafe"}'

- List transactions:
  Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8000/api/accounts/{id}/transactions/' | ConvertTo-Json

Notes about endpoints and semantics
- Savings is an earmarked portion of the account total — allocating money to savings reduces spendable by the same amount so total is not double-counted.
- Expenses default to spendable. To spend from savings, set allocation="savings" explicitly in the expense request.
- Transfers between allocations do not alter account.total_balance.


Change log / Future improvements
- Add authentication/authorization (DRF Token or JWT).
- Add pagination to transactions endpoint.
- Add categories and tags for transactions.
- Add export endpoints (CSV) and report endpoints (monthly trends) — planned in Phase 8.

