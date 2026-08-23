Created isolated worktree for branch `agents/expense-tracking-savings-spendable`

Clarifying how "savings" should behave is the next critical step because it changes the database model, APIs, and UI flows. Choose one of the two behavior models so the phase plan and concrete tasks can be created correctly. I'll recommend the most typical/safe option.

Asking which savings model to use (pick one):

Ask User
Completed with input: {
  "question": "Which savings allocation model should the project implement? (Recommended: option 1)",
  "choices": [
    "Savings is an earmarked portion of the source balance: allocating to savings reduces the spendable amount (Recommended)",
    "Savings is an independent copy: both savings and spendable hold copies of the same deposited money and may double-count the total available"
  ]
}

Thanks — choice recorded: "Savings is an earmarked portion of the source balance: allocating to savings reduces the spendable amount."

Below is a clear, phased plan (nuclear phases) and concrete artifacts you can implement manually. Each phase includes tasks, acceptance criteria, DB schema/migrations, Django models and API contracts, frontend components, JS snippets, edge cases, and tests. Follow the phases in order; stop after each phase to verify acceptance criteria before proceeding.

Summary of chosen business rule (used throughout the plan)
- There is a single source "Account" balance per payment source (e.g., GPay).
- When money is deposited into an Account, the amount is added to account.total_balance.
- Users allocate portions of that total to two buckets:
  - spendable — funds available for expenses (default for expenses)
  - savings — earmarked portion that is not spendable unless explicitly spent/transferred
- Allocating to savings reduces spendable so that spendable + savings = total_balance (no double-counting).
- Expenses are deducted from spendable by default; the user can choose to spend from savings (which will reduce savings and total_balance, and may adjust spendable if you choose to auto-rebalance — see options below).

Phase 0 — Environment & Project Setup (preparation)
- Tasks:
  1. Create project folder in C:\pg_expense and initialize git (you already have it).
  2. Create Python virtualenv and install Django and psycopg2-binary.
  3. Create Django project (e.g., project name `pg_expense`) and app (e.g., `wallet`).
  4. Configure settings for PostgreSQL (DB credentials, host, port).
  5. Install frontend tooling (plain HTML/CSS/JS; optional dev server).
- Acceptance criteria:
  - Django dev server runs, connects to Postgres, and shows default page.
  - README notes setup steps.
- Notes: Keep secrets (DB password) out of repo; use environment variables or a .env file ignored by git.

Phase 1 — Core Models and DB Schema
- DB tables to add (Django models):
  1. Account
     - id (UUID)
     - name (string, e.g., "GPay")
     - total_balance (decimal, scale 2)
     - currency (string, default "INR")
     - created_at, updated_at
  2. Allocation (per Account)
     - id (UUID)
     - account (FK -> Account)
     - type (enum: 'spendable' | 'savings')
     - balance (decimal)
     - created_at, updated_at
     - Unique constraint: account + type
  3. Transaction
     - id (UUID)
     - account (FK -> Account)
     - allocation (FK -> Allocation) — nullable for some transfers
     - type (enum: 'deposit' | 'expense' | 'allocation' | 'transfer')
     - amount (decimal, positive)
     - metadata (JSON/text) — notes, merchant
     - created_at
     - related_tx (self FK) — optional, to link transfer pairs
- Migration steps:
  - Create models and run makemigrations/migrate.
- Initial data:
  - When creating an Account, create two Allocation rows:
    - spendable with balance = 0.00
    - savings with balance = 0.00
- Acceptance criteria:
  - Accounts and Allocations can be CRUDed.
  - spendable.balance + savings.balance == account.total_balance at all times.

Phase 2 — Business Logic: Deposits, Allocation, and Reconciliation
- Goal: Implement rules so deposits and allocations keep totals consistent.
- Rules (implementation details):
  1. Deposit flow:
     - API: POST /api/accounts/{id}/deposit/
     - Body: {amount: number, allocate_to_savings: number (optional), note: string}
     - Behavior:
       - Increment account.total_balance by amount.
       - If allocate_to_savings provided (amount or percentage), move that amount into Allocation.savings.balance and the rest into Allocation.spendable.balance.
       - If allocate_to_savings not provided, default: put entire deposit into spendable.
     - Ensure spendable + savings == total_balance
  2. Manual allocation (move between buckets):
     - API: POST /api/accounts/{id}/allocate/
     - Body: {from: 'spendable'|'savings', to: 'spendable'|'savings', amount}
     - Behavior:
       - Subtract amount from source allocation, add to destination, no change to account.total_balance.
       - Prevent negative source balances.
  3. Auto-allocation rules:
     - Optionally support allocation percentages per account/profile, applied on deposit.
- Acceptance criteria:
  - After deposit and allocation, totals reconcile.
  - Moves between allocations don't change account.total_balance.

Phase 3 — Spending (Expenses) and Optional Spending from Savings
- Goal: Allow creating expenses that reduce balances correctly.
- API:
  - POST /api/accounts/{id}/expense/
  - Body: {amount: number, allocation: 'spendable'|'savings' (default 'spendable'), merchant: string, note: string}
- Behavior:
  1. Default: allocation='spendable'
     - Deduct amount from Allocation.spendable.balance and account.total_balance.
  2. If allocation='savings' (explicit):
     - Deduct amount from Allocation.savings.balance and account.total_balance.
  3. Prevent overspend:
     - Return 400 with readable message if allocation.balance < amount.
  4. Optional: auto-rebalance when spendable insufficient — two options:
     - Hard block (recommended): prevent spending if insufficient unless explicit transfer from savings to spendable occurs.
     - Allow draw from savings automatically: if spendable < amount and user allows, deduct remainder from savings and mark a combined transaction (requires UX clarity).
- Transaction recording:
  - Each expense creates a Transaction row (type='expense') linked to allocation and account.
- Acceptance criteria:
  - Expense reduces allocation and account totals.
  - Overspend is prevented or controlled per chosen policy.

Phase 4 — Transfers & Savings "copy" semantics (as per requirement)
- Clarification: Since chosen model earmarks savings and reduces spendable, implement “copy” behavior as “earmarking” (not duplicate money).
- Transfer flows:
  1. Transfer from Account to Savings (earmarking):
     - POST /api/accounts/{id}/transfer-to-savings/
     - Body: {amount}
     - Behavior: Subtract amount from spendable.balance, add to savings.balance; total_balance unchanged.
  2. Transfer from Savings to Spendable (un-earmark):
     - POST /api/accounts/{id}/transfer-to-spendable/
     - Body: {amount}
     - Behavior: subtract savings, add spendable.
- Acceptance criteria:
  - Transfers update only allocations (not total_balance).
  - All transfers are recorded as Transaction type 'transfer' (linked pair if desired).

Phase 5 — API Design and Contracts (examples)
- Endpoints (suggested):
  - GET /api/accounts/ — list accounts with allocations
  - POST /api/accounts/ — create account (creates allocations)
  - GET /api/accounts/{id}/ — account details including allocations
  - POST /api/accounts/{id}/deposit/ — deposit money (see payload earlier)
  - POST /api/accounts/{id}/allocate/ — move between allocations
  - POST /api/accounts/{id}/expense/ — create expense
  - POST /api/accounts/{id}/transfer-to-savings/ — earmark
  - POST /api/accounts/{id}/transfer-to-spendable/ — un-earmark
  - GET /api/accounts/{id}/transactions/ — list transactions
- Example JSON responses:
  - Account details:
    {
      "id": "uuid",
      "name": "GPay",
      "currency": "INR",
      "total_balance": "1000.00",
      "allocations": {
         "spendable": "700.00",
         "savings": "300.00"
      }
    }
- Authentication:
  - Add token-based auth (DRF Token or JWT) if multiple users; otherwise simple session auth.

Phase 6 — Frontend (HTML/CSS/JS) Components & UX Flows
- Pages/components:
  1. Dashboard (list accounts and balances; show allocations)
  2. Account detail modal/page (list transactions, create deposit, quick transfer, create expense)
  3. Create Deposit dialog:
     - Inputs: amount, allocate_to_savings (number or %), apply button
     - After submit, show success and updated balances
  4. Expense dialog:
     - Inputs: amount, allocation (default spendable), merchant, note
  5. Quick transfer between allocations
- JS snippets (example fetch for expense):
  - POST fetch('/api/accounts/{id}/expense/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({amount:100, allocation:'spendable', merchant:'Cafe'})})
  - On 200, update UI with returned balances; on 400 show error.
- UI validation:
  - Prevent entering non-numeric amounts, show currency formatting.
  - Warn before spending from savings.
- UX edge cases:
  - Show clear visual separation of spendable vs savings.
  - Show total_balance as authoritative.

Phase 7 — Tests, QA, and Edge Cases
- Backend unit tests:
  - Account creation initializes allocations.
  - Deposit with allocation percentages updates allocations correctly.
  - Transfer between allocations conserves total_balance.
  - Expense reduces allocation and account totals or returns 400 on insufficient funds.
- Integration tests:
  - Simulate deposit -> allocation -> expense -> reconciliation.
- Edge cases to test:
  - Concurrent deposits/expenses: use DB transactions and SELECT ... FOR UPDATE or Django F() operations to avoid race conditions.
  - Negative/zero amounts.
  - Floating point vs decimal precision (use DecimalField with max_digits and decimal_places).
- Acceptance criteria:
  - All tests pass locally.
  - Manual reconciliation: sum(allocations) == account.total_balance for multiple accounts.

Phase 8 — Reporting, Exports & UX Refinements
- Reporting features:
  - Monthly expense by category/merchant.
  - Savings trend graph (savings over time).
  - Export transactions to CSV.
- UX:
  - Ability to set default allocation percentages.
  - Notifications when spendable below threshold.
  - Undo last transaction within short window.

Phase 9 — Deployment & Operational
- Dockerize Django app (optional), configure connection to Postgres.
- Migrations: use `python manage.py migrate` on deploy.
- Backups for Postgres.
- Environment variables for DB credentials and secret key.

Concrete Django model snippet (starter)
- This is a plain reference for you to implement in the wallet app models.py:

  - Account model with DecimalField total_balance
  - Allocation model with type choices and balance
  - Transaction model as described above

(If you want, I can produce the exact model code, migration notes, and DRF serializers/views next.)

Concurrency and consistency recommendations (must implement)
- Use database transactions around operations that update balances.
- Use F() expressions in Django to update balances atomically:
  - Allocation.objects.filter(...).update(balance=F('balance') - amount)
- Validate preconditions (e.g., allocation.balance >= amount) using select_for_update or in-database check + rollback.

Security & Data Integrity
- Validate and sanitize all inputs.
- Use Decimal (not float) for money.
- Store currency and handle conversions if multiple currencies come later.
- Audit trail: keep Transaction rows immutable; to correct mistakes create inverse transactions.

Suggested small milestone checklist (ready-to-run manual tasks)
1. Setup Django project, create wallet app, configure Postgres.
2. Implement models and initial migration; create an Account & allocations.
3. Implement deposits and allocation API; test via curl/Postman.
4. Implement expense API with safeguards; test error flows.
5. Build minimal frontend: dashboard + account page; wire API calls.
6. Add unit tests for balance invariants.
7. Add transfer API and UI.
8. Add reporting & polish.

If you want, next steps I can provide (pick one):
- Full Django models.py + serializers + views + urls + sample migrations.
- Complete API spec (OpenAPI style) for copy-paste.
- Example frontend HTML/CSS/JS pages and exact fetch() code to wire to endpoints.
- A prioritized todo list you can paste into the repo's task tracker.

Which artifact should be produced next? (Use the UI choice below)
- Provide models + migrations + DRF views and serializers (Recommended)
- Provide complete API spec / OpenAPI
- Provide frontend HTML/CSS/JS scaffolding and example pages
- Provide unit/integration test examples and commands