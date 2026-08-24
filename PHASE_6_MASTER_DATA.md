# PHASE 6 — MASTER DATA & CONFIGURATION

Status: implemented; local regression verification required.

## Implemented

- Account lifecycle: create, edit, archive/reactivate.
- Accounts with non-zero balances cannot be archived.
- Category lifecycle: create, edit, archive/reactivate.
- Archiving a category archives its subcategories and items so historical transaction foreign keys remain valid.
- Subcategory lifecycle: create, edit, archive/reactivate.
- Archiving a subcategory archives its items.
- Item lifecycle: create, edit, archive/reactivate.
- Owner lifecycle: create, edit, archive/reactivate.
- MoneyLocation lifecycle: create, edit, archive/reactivate.
- A money location used by an active account cannot be archived.
- Configuration defaults are persisted through AppSetting and validated against active owners/locations.
- Transaction-facing serializer selectors now reject inactive categories, subcategories, items, owners and money locations.
- Canonical Phase 6 management UI: `/api/master-data/page/`.
- Canonical Phase 6 API namespace: `/api/master-data/`.
- Added regression tests covering lifecycle, hierarchy, configuration and page protection.

## Design rule

Master data is deactivated rather than hard-deleted. Existing transactions therefore retain their historical foreign-key references and remain readable.

## Verification gate

Run:

```powershell
python manage.py test
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

Expected final conditions:

- all tests pass
- no unapplied migrations
- no model changes detected
