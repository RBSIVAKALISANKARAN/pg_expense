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
- 7.9 Desktop, tablet and mobile viewport smoke coverage
- 7.10 Settings page removal / 404 verification

The browser suite is deliberately separate from `python manage.py test`: the backend regression suite remains the fast regression suite, while this suite validates the actual user interface in Chromium.
