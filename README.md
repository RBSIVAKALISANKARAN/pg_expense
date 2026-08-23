## Docker setup

You can run the project in containers with Docker Compose.

1. Ensure Docker Desktop or Docker Engine is installed.
2. From the project root, run:
   ```powershell
   docker compose up --build
   ```
3. The app will be available at:
   - Web app: http://localhost:8000
   - PostgreSQL: localhost:5432

### Container configuration
- `web` runs the Django app with Gunicorn.
- `db` runs PostgreSQL 16.
- Environment variables are read from the local shell or `.env` if present.

### Useful commands
```powershell
docker compose up --build
docker compose down
docker compose logs -f web
docker compose exec db psql -U postgres -d expense
```
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
- SQL Playground: http://127.0.0.1:8000/api/sql/
- API docs: API_DOCS.md
- Project notes: NOTES.md

The SQL Playground is a safe, read-only interface for running PostgreSQL queries against the finance database. It supports schema browsing, saved queries, and execution history while blocking destructive commands.

## Running tests
Run unit tests for the wallet app:
```powershell
python manage.py test wallet
```

## Next steps
See API_DOCS.md and NOTES.md for detailed API usage, data model explanation, and development notes.

