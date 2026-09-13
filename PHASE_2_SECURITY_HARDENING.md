# Phase 2 — Security hardening

Implemented:

- Django HSTS and `X-Content-Type-Options: nosniff` enforcement.
- Native Django Content-Security-Policy middleware with an enforced same-origin baseline.
- Global DRF anonymous/user throttling plus a stricter scoped throttle for SQL execution.
- Exact version pins for application dependencies.
- `pip-audit` and `bandit` included in the pinned security toolchain.
- SQL Playground restricted to Django staff users at both page and API boundaries.
- SQL execution retains read-only transactions, statement timeout, row caps, and audit logging.
- Non-staff navigation no longer exposes the SQL Playground.

Validation commands:

```powershell
python manage.py check
python manage.py test
python manage.py check --deploy
pip-audit -r requirements.txt
bandit -r wallet pg_expense -x wallet/migrations
```

Note: the current UI still contains inline JavaScript/CSS, so the enforced CSP allows `unsafe-inline` for those two resource types. The policy still blocks external origins, plugins/objects, cross-origin framing, and non-self form/base targets. A future frontend refactor can replace `unsafe-inline` with Django CSP nonces.
