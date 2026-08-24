# Phase 3 — Core UI Completion

## Implemented on demo

### 3.1 Settings persistence
- Added `AppSetting` database model.
- Added migration `0021_appsetting`.
- Replaced hard-coded settings API/page with persistent settings implementation.
- General preferences can be saved and survive reloads/restarts.
- Invalid default allocation values are rejected.
- Removed fake profile/2FA controls that did not have real backend behavior.

### 3.2 Savings ↔ Spendable UI
- Accounts page now exposes real Savings and Spendable allocation controls.
- Existing transactional endpoints are used; the UI does not manipulate balances directly.
- Total account balance is preserved during allocation transfers.

### 3.3 Dashboard cleanup
- Removed duplicate master-data creation controls from Dashboard.
- Categories page remains responsible for category/subcategory/item management.
- Dashboard now focuses on financial overview, wallets, recent activity and navigation.

### 3.4 Reports
- Replaced placeholder Reports page with live analytics cards and breakdowns.
- Uses the existing `/api/reports/data/` ledger-backed endpoint.
- Added refresh behavior and escaped API-derived display values.

### 3.5 Sidebar
- Added functional collapse/expand behavior.
- State is persisted in localStorage.
- Added responsive mobile behavior.

## Verification required

Run locally:

```powershell
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py test
```

Phase 3 is not considered closed until the test suite and migration checks are green and the changed UI pages are manually browser-verified.
