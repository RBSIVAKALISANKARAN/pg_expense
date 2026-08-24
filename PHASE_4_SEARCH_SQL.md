# Phase 4 — Search, Filtering & SQL Playground

## Completed

### 4.1 Transaction search and filters
- Global transaction search across wallet/account, owner, money location, category, subcategory, item, variant, merchant, note, custom description and transaction type.
- Filters for wallet, owner, transaction type, category, allocation, and date range.
- Apply and Reset controls in the transaction ledger.
- Filter option endpoint is authenticated.
- Results are capped at 500 rows per request.

### 4.2 SQL schema explorer
- Canonical `/api/sql/schema/` and `/api/sql/schema-live/` now require authentication.
- Schema response contains live PostgreSQL tables and columns.

### 4.3 SQL editor workflow
- Existing secure SQL execution remains the canonical executor.
- Read-only transaction enforcement, timeout and row limit from Phase 1/2 are preserved.
- Query history is available through an authenticated endpoint.
- Saved queries are available through authenticated list/detail/delete operations.
- Saved queries are validated with the same read-only SQL validator used by execution, so blocked write/destructive statements cannot be saved as executable queries.

### Verification
Run `python manage.py test`, `python manage.py migrate`, and `python manage.py makemigrations --check --dry-run` locally before closing the phase.
