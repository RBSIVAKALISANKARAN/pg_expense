# Phase 7 — Browser & UI Automated Testing

These tests exercise the application through a real Chromium browser. They intentionally cover HTML rendering, navigation, JavaScript interactions, forms, buttons, persistence and responsive viewports rather than Django request-level behavior.

## Install

```powershell
pip install -r requirements-e2e.txt
python -m playwright install chromium
```

## Start the application

Run the Django development server in one terminal:

```powershell
python manage.py runserver 127.0.0.1:8000
```

Create or use an authenticated Django user. In PowerShell, set the browser-test credentials:

```powershell
$env:E2E_USERNAME="your_username"
$env:E2E_PASSWORD="your_password"
$env:E2E_BASE_URL="http://127.0.0.1:8000"
```

Then, from a second terminal:

```powershell
pytest e2e/test_phase7.py -v
```

## Coverage

- 7.1 Dashboard smoke/navigation
- 7.2 Account creation, deposit, transfer and balance reconciliation
- 7.3 Expense form submission and balance reconciliation
- 7.4 Transaction search, edit, revert and soft-delete
- 7.5 Category master-data creation
- 7.6 Spendable ↔ Savings browser workflow
- 7.7 SQL Playground schema/history/results interaction
- 7.8 Reports page rendering
- 7.9 Settings save + reload persistence
- 7.10 Desktop, tablet and mobile viewport smoke coverage

The browser suite is deliberately separate from `python manage.py test`: the existing 76 backend tests remain the fast regression suite, while this suite validates the actual user interface in Chromium.
