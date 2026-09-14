# PG Expense

Personal expense-tracking application built with Django and Django REST Framework.

## API documentation

The live API reference is generated from the running API with drf-spectacular:

- Swagger UI: `/api/docs/`
- Raw OpenAPI 3 schema: `/api/schema/`

## API response convention

This project intentionally keeps successful responses in their existing domain shape (for example, a resource object, a list, or a simple `{"detail": "..."}` response). Wrapping successful responses in a new `{"data": ...}` envelope would require coordinated frontend changes without providing a functional benefit here.

Errors use the normalized shape `{"detail": "...", "errors": {...}}` where additional field-level or structured error information is available.

## Phase 4 authentication migration

Phase 4 introduces the project-owned `wallet.User` custom user model before production. The development migration history has been reset to a fresh `wallet/migrations/0001_initial.py`, followed by `0002_seed_standard_wallets.py`; the standard-wallet seed logic now lives in `wallet/seeds.py` so it survives future migration resets.

This migration reset intentionally targets the development database only. Before using the branch against a fresh environment, recreate the PostgreSQL `expense` database and run `python manage.py migrate`.
