Project Notes — Expense Tracking (Savings + Spendable)

Overview
- Purpose: Track money held in payment sources (accounts such as GPay, bank accounts), split each account into two allocations: spendable and savings. Expenses reduce allocations and the account total.
- Tech stack: Django (backend), Django REST Framework, PostgreSQL; frontend: minimal HTML/JS (no framework).

Key business rule (chosen)
- Savings is an earmarked portion of the same account balance. That means:
  total_balance == spendable.balance + savings.balance
- When deposit occurs, user may allocate a portion to savings; the remainder is spendable.
- Expenses are deducted from the chosen allocation and reduce total_balance.

Database model
- Account
  - id: UUID primary key
  - name: string
  - total_balance: Decimal(12,2)
  - currency: string (default 'INR')
  - created_at, updated_at

- Allocation
  - id: UUID
  - account: FK -> Account
  - type: 'spendable' | 'savings'
  - balance: Decimal(12,2)
  - Unique constraint on (account, type)

- Transaction
  - id: UUID
  - account: FK
  - allocation: FK to Allocation (nullable)
  - type: 'deposit'|'expense'|'allocation'|'transfer'
  - amount: Decimal
  - metadata: JSONField for merchant, note, direction
  - created_at
  - related_tx: FK to self (nullable) for paired transfers

Concurrency and integrity
- All operations that modify balances are wrapped in transaction.atomic() and use select_for_update() to prevent race conditions.
- F() expressions update money fields atomically in the DB.
- After F() updates, objects are refreshed from DB to read concrete values.

Running locally (developer steps)
1. Ensure PostgreSQL is running and database exists (name: expense by default). Update .env if needed.
2. From project root (C:\pg_expense):
   - . .\.venv\Scripts\Activate.ps1   (PowerShell: dot, space, path)
   - pip install -r requirements.txt
   - python manage.py migrate
   - python manage.py createsuperuser  (optional)
   - python manage.py runserver
3. Visit http://127.0.0.1:8000/ — root redirects to /admin/.
4. API base: http://127.0.0.1:8000/api/

Testing
- Unit tests are in wallet/tests.py. To run:
  . .\.venv\Scripts\Activate.ps1
  python manage.py test wallet

Files of interest
- wallet/models.py  — data models
- wallet/views.py   — API view logic with atomic updates
- wallet/serializers.py — DRF serializers
- wallet/urls.py    — API routes
- pg_expense/settings.py — Django settings, DB configuration reads from .env
- pg_expense/templates/dashboard.html — minimal frontend
- API_DOCS.md, NOTES.md — documentation files (this and API docs)

Admin
- Django admin available at /admin/. Use the admin to inspect accounts, allocations and transactions. Superuser was created earlier (admin/admin123) in this environment; change in production.

Security and secrets
- .env holds SECRET_KEY and DB credentials. Ensure .env is listed in .gitignore (it is).
- If .env was ever committed, rotate credentials and remove from Git history.

Next planned phases
- Phase 5: API docs/UI improvements (add swagger or DRF schema endpoints)
- Phase 6: Full frontend (forms to create accounts, deposit, expense, transfers; better UX)
- Phase 8: Reporting endpoints (CSV export, monthly trend)
- Phase 9: Deployment (Dockerfile, compose, production settings)

Notes for contributors
- Use Decimal strings in JSON to avoid float rounding issues.
- When changing balance logic, add/update tests that assert spendable+savings == total_balance.
- Use select_for_update and transaction.atomic() for any new endpoint that modifies balances.

How to extend
- Add per-user accounts and tie Account.user = FK(User) for multi-user system.
- Add categories and budgets: category table + transaction.category FK; budget rules can auto-allocate notifications.
- Add scheduled transfers and recurring allocations (cron or Celery + periodic tasks).

Contact / Ownership
- Repo owner: You (local)
- This environment: local development machine (C:\pg_expense)

