# Phase 3 — Core UI Completion

## Implemented on `demo`

### 3.1 Settings persistence
- Added `AppSetting` database model and migration `0021_appsetting`.
- Settings are persisted in PostgreSQL and survive reloads/restarts.
- Invalid allocation settings are rejected.
- Removed non-functional profile/2FA controls.
- Settings page requires authentication.

### 3.2 Savings ↔ Spendable UI
- Accounts page exposes real Savings and Spendable allocation controls.
- Existing transactional endpoints are used; the UI does not manipulate balances directly.
- Total account balance is preserved during allocation transfers.

### 3.3 Dashboard cleanup
- Removed duplicate master-data creation controls from Dashboard.
- Categories remains responsible for category/subcategory/item management.
- Dashboard focuses on financial overview, wallets, recent activity and navigation.
- Sidebar collapse/expand state persists in localStorage and responds to mobile layouts.

### 3.4 Reports
- Replaced the placeholder Reports page with live analytics cards and ledger-backed breakdowns.
- Added refresh behavior, empty-state handling and escaped API-derived display values.

### 3.5 Transaction UI completion
- Transactions page requires authentication.
- Added explicit loading, empty and error states.
- Added refresh control.
- Edit validates positive amounts before submission.
- Edit/revert/delete controls disable while processing and surface API errors without losing the current ledger state.
- Dynamic transaction values remain HTML-escaped.
- Successful edits/reverts/deletes refresh the ledger.

### 3.6 Page/API contract coverage
- Added regression tests for authenticated transaction-page access.
- Added dashboard reachability after login.
- Added settings persistence rendering coverage.
- Added authenticated report-data coverage.

## Verification

Run locally:

```powershell
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py test
```

Phase 3 should only be closed after those checks are green and the changed pages have been manually opened in the browser while authenticated. Verify Settings, Accounts, Dashboard, Transactions, Reports and Sidebar behavior, including empty/error/loading states.
