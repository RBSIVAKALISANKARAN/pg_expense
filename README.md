# Expense Tracking Savings Spendable

## Prerequisites
- Python 3.10+
- PostgreSQL 16
- Git

## Setup
1. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and update values if needed.
4. Ensure the PostgreSQL database `expense` exists and is reachable.
5. Apply migrations:
   ```powershell
   python manage.py migrate
   ```
6. Create an admin user:
   ```powershell
   python manage.py createsuperuser
   ```
7. Run the dev server:
   ```powershell
   python manage.py runserver
   ```
8. Open `http://127.0.0.1:8000`

## Database configuration
The app uses environment variables from `.env`:
- `DB_NAME=expense`
- `DB_USER=postgres`
- `DB_PASSWORD=421688`
- `DB_HOST=localhost`
- `DB_PORT=5432`

## Notes
This project uses Django with PostgreSQL and a wallet app that implements "savings" and "spendable" allocations per account.

- Dashboard (minimal): http://127.0.0.1:8000/api/dashboard/
- API docs: API_DOCS.md
- Project notes: NOTES.md

## Running tests
Run unit tests for the wallet app:
```powershell
python manage.py test wallet
```

## Next steps
See API_DOCS.md and NOTES.md for detailed API usage, data model explanation, and development notes.
