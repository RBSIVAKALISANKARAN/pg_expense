# PG Expense — Phase 0 Baseline

**Phase:** 0 — Baseline & Safety  
**Working branch:** `demo`  
**Baseline commit:** `5f9021f599d8939bf2efe1f89b97c9212e63358a`  
**Baseline commit message:** `account name correction`  
**Baseline date:** 2026-08-24

## Purpose

Phase 0 establishes a fixed, documented starting point before remediation work begins. Later phases must preserve the existing financial behavior unless a deliberate requirement changes it.

## Repository baseline

- Repository: `RBSIVAKALISANKARAN/pg_expense`
- Branch for remediation: `demo`
- Default application: Django + Django REST Framework
- Database backend configured: PostgreSQL
- Main application: `wallet`
- Time zone: `Asia/Kolkata`
- Environment file support: `.env` is ignored by Git

## Current structure observed at baseline

### Project

- `manage.py`
- `pg_expense/settings.py`
- `pg_expense/urls.py`
- `pg_expense/asgi.py`
- `pg_expense/wsgi.py`

### Application

The `wallet` application contains the financial models, serializers, views, reporting, migrations, management commands and supporting feature modules.

### Frontend/templates

The project currently contains pages for:

- Dashboard
- Accounts
- Expense
- Transactions
- Categories
- Reports
- Settings
- SQL Playground
- Database Structure

There are also enhanced/alternate template implementations that will be investigated during the architecture-cleanup phase. They are **not removed in Phase 0**.

## Safety rules established by Phase 0

1. Work on `demo` unless a later phase explicitly says otherwise.
2. Do not modify `main` as part of remediation.
3. Do not redesign working financial logic without a requirement and regression test.
4. Do not create a second database or parallel financial model.
5. Do not delete legacy implementations until their routes/dependencies have been traced and the canonical implementation has been verified.
6. Every remediation sub-phase must finish with relevant tests/verification before the next sub-phase begins.
7. Keep commits small and descriptive so each sub-phase can be reverted independently.
8. Preserve historical migrations; do not rewrite old migrations merely to make current code look cleaner.

## Security observations captured — not fixed in Phase 0

The current settings contain development defaults that are intentionally recorded here for Phase 1/8 remediation:

- `DEBUG` defaults to `True`.
- `ALLOWED_HOSTS` is currently `['*']`.
- `SECRET_KEY` has a development fallback.
- Database configuration has a development password fallback.

These are findings to remediate later; Phase 0 does not change application security behavior.

## Test baseline

The previous consolidated audit reported **38/38 backend tests passing** on the audited state. Because Phase 0 is being applied directly to the `demo` branch through repository operations, this document does not claim that the GitHub connector itself executed those tests.

Required local baseline command before Phase 1:

```text
python manage.py test
```

Expected baseline: all existing backend tests pass before security/feature changes begin.

## Phase 0 completion criteria

- [x] `demo` branch identified and confirmed.
- [x] Exact baseline commit recorded.
- [x] Repository/application structure recorded.
- [x] Safety rules recorded.
- [x] Known security observations recorded without changing behavior.
- [ ] Backend test command executed in a runtime environment and baseline result recorded.
- [ ] Git checkpoint/backup exists outside GitHub.

The remaining two items require an actual project runtime/local environment and are intentionally not fabricated by this repository-only operation.

## Next phase

**Phase 1 — Security & Access Control**

Phase 1 should begin only after the local `python manage.py test` baseline is confirmed green.
