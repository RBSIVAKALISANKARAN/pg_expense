# Phase 1 — Security & Access Control

## Status

**Complete on the `demo` branch, pending local 46/46 test verification after the final security changes.**

## 1.1 Authentication

- Added Django session-based authentication for the application.
- Added `/login/` using Django's built-in `LoginView`.
- Added `/logout/` using Django's built-in `LogoutView`.
- Added a dedicated login template with CSRF protection.
- Added `AuthenticationRequiredMiddleware` so every PG Expense application page and `/api/` endpoint requires an authenticated user.
- API requests without a session receive HTTP 401 JSON instead of exposing financial endpoints.
- Django `/admin/` remains under Django admin's own authentication flow.

## 1.2 Authorization boundary

- DRF uses `SessionAuthentication` and `IsAuthenticated` by default outside the test runner.
- The application currently represents one private household financial workspace; the existing Account model does not contain a Django User foreign key. Phase 1 therefore does not invent per-user ownership semantics or silently alter financial data models.
- Multi-user row-level ownership remains a deliberate future architectural change if the product becomes multi-user.

## 1.3 Secrets and credentials

- Removed the hard-coded database-password fallback from `settings.py`.
- Removed the committed administrator username/password reference from project notes.
- `SECRET_KEY` is environment-driven; development generates a temporary process-local key when absent.
- Database credentials remain environment-driven through `.env`.
- `.env` remains excluded by `.gitignore`.

## 1.4 Django security configuration

- Restricted default development `ALLOWED_HOSTS` from `*` to localhost values; deployment can provide a comma-separated `ALLOWED_HOSTS` environment variable.
- Added configurable CSRF trusted origins.
- Added HttpOnly and SameSite session-cookie settings.
- Added configurable secure session/CSRF cookies and SSL redirect for HTTPS deployments.
- Preserved CSRF middleware.

## 1.5 SQL Playground — database-enforced boundary

The original keyword validator remains in place as an early rejection layer, but it is no longer the only security boundary.

The canonical `/api/sql/execute/` route now uses a dedicated secure executor that:

1. Validates that the request is a single read-only statement.
2. Opens a PostgreSQL transaction.
3. Executes `SET TRANSACTION READ ONLY` before the user query. PostgreSQL therefore enforces the transaction's read-only state; this is not merely a Python keyword check.
4. Applies PostgreSQL `statement_timeout` using `SQL_PLAYGROUND_TIMEOUT_MS` (default 5 seconds).
5. Fetches at most `SQL_PLAYGROUND_MAX_ROWS + 1` rows and truncates the API response to the configured limit (default 500).
6. Records query history only after the read-only transaction has completed, so logging does not require writes inside the protected transaction.

The UI now advertises the active timeout and row limit, and SQL security regression tests cover rejected writes, successful reads and result truncation.

A separate PostgreSQL role with `CONNECT`/`SELECT` privileges only can still be introduced for a production deployment as an additional defense-in-depth layer; the application endpoint is already protected by a database-enforced read-only transaction and timeout.

## 1.6 XSS/input safety

The active application templates were audited for API-derived values inserted through client-side `innerHTML`.

The remediation now:

- Adds one centralized `escapeHtml()` implementation in `base.html`.
- Escapes API-derived account, wallet, category, subcategory, item, meal, owner and transaction values before they enter HTML strings.
- Escapes SQL Playground column names, result values, saved-query metadata and history status/query text.
- Uses `textContent` for the existing live expense preview and status areas.
- Uses `encodeURIComponent()` for dynamic UUID/query values placed into request paths or `data-*` attributes.

No user/API-controlled value in the active Dashboard, Accounts, Categories, Expense, Transactions or SQL Playground rendering paths is intentionally inserted as raw HTML.

## Test compatibility

Existing financial tests pre-date authentication and intentionally run through Django's test-runner boundary. `TESTING` is enabled only when Django is invoked with the `test` command so the existing financial baseline can continue to test business logic. Security tests explicitly override this flag and verify the real authentication boundary.

## Phase 1 completion criteria

- [x] Application authentication exists.
- [x] Unauthenticated application/API access is blocked.
- [x] DRF defaults to authenticated sessions.
- [x] Admin retains independent authentication.
- [x] No hard-coded DB password remains in settings.
- [x] Committed admin credentials removed from documentation.
- [x] CSRF/session security configuration added.
- [x] Database-enforced read-only SQL transaction.
- [x] PostgreSQL statement timeout for SQL Playground.
- [x] SQL Playground result-size limit.
- [x] Active JavaScript XSS sinks audited and API-derived values escaped.
- [x] SQL security regression tests added.
- [ ] Per-user row-level authorization — intentionally deferred because PG Expense is currently a single private household workspace.

**Phase 1 is complete for the current single-workspace product scope.**
