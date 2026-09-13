# Security Tooling

Run these commands from the project virtual environment before releases:

```powershell
pip-audit -r requirements.txt
bandit -r wallet pg_expense -x wallet/migrations
python manage.py check --deploy
```

`pip-audit` checks installed/project dependencies against known Python package vulnerabilities. `bandit` scans the Python source tree for common security anti-patterns. These tools are intentionally kept in `requirements.txt` so the audit toolchain is version-pinned with the application dependencies.
