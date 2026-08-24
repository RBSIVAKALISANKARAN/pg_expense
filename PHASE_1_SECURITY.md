# Phase 1 — Security & Access Control

## Status

Implemented on the `demo` branch.

## 1.1 Authentication

- Added Django session-based authentication for the application.
- Added `/login/` using Django's built-in `LoginView`.
- Added `/logout/` using Django's built-in `LogoutView`.
- Added a dedicated login template with CSRF protection.
- Added `AuthenticationRequiredMiddleware` so every PG Expense application page and `/api/` endpoint requires an authenticated user.
- API requests without a session receive HTTP 401 JSON instead of exposing financial endpoints.
- Django `/admin/` remains under Django admin's own authentication flow.

## 1.2 Authorization boundary

- DRF now uses `SessionAuthentication` and `IsAuthenticated` by default outside the test runner.
- The application currently represents one private household financial workspace; the existing Account model does not contain a Django User foreign key. Therefore Phase 1 does **not** invent per-user ownership semantics or silently alter financial data models.
- Multi-user row-level ownership (`Account.user` and corresponding queryset scoping) remains a deliberate future architectural change and is documented in the existing project notes.

## 1.3 Secrets and credentials

- Removed the hard-coded database-password fallback from `settings.py`.
- Removed the committed administrator username/password reference from project notes.
- `SECRET_KEY` is now environment-driven; development generates a temporary process-local key when absent.
- Database credentials remain environment-driven through `.env`.
- `.env` remains excluded by `.gitignore`.

## 1.4 Django security configuration

- Restricted the default development `ALLOWED_HOSTS` from `*` to localhost values; deployment can provide a comma-separated `ALLOWED_HOSTS` environment variable.
- Added configurable CSRF trusted origins.
- Added HttpOnly and SameSite session-cookie settings.
- Added configurable secure session/CSRF cookies and SSL redirect for HTTPS deployments.
- Preserved CSRF middleware.

## 1.5 SQL Playground

The existing SQL validator already rejects destructive SQL keywords and multiple statements. Phase 1 preserves that working behavior.

A database-level read-only SQL user, statement timeout, and result-size enforcement require the actual PostgreSQL deployment role/configuration and will be completed as part of the SQL hardening work in the SQL Playground phase rather than pretending a Python keyword filter is equivalent to database isolation.

## 1.6 XSS/input safety

Django templates use normal template autoescaping by default. The repository still contains client-side `innerHTML` rendering paths that need a complete JavaScript sink audit. Those paths are not being falsely marked fixed in Phase 1; the remaining sink-by-sink remediation belongs in the security/browser hardening work.

## Test compatibility

Existing financial tests pre-date authentication and intentionally run through Django's test-runner boundary. `TESTING` is enabled only when Django is invoked with the `test` command so the existing 38/38 financial baseline can continue to test business logic. `wallet/test_security.py` explicitly overrides this flag and verifies the real authentication boundary.

## Phase 1 completion criteria

- [x] Application authentication exists.
- [x] Unauthenticated application/API access is blocked.
- [x] DRF defaults to authenticated sessions.
- [x] Admin retains independent authentication.
- [x] No hard-coded DB password remains in settings.
- [x] Committed admin credentials removed from documentation.
- [x] CSRF/session security configuration added.
- [x] Security regression tests added.
- [ ] Database-level SQL read-only role + timeout/result limits.
- [ ] Complete JavaScript XSS sink audit.
- [ ] Per-user row-level authorization, if the product becomes multi-user.

Those unchecked items are intentionally not represented as complete; they remain explicit follow-up work.
