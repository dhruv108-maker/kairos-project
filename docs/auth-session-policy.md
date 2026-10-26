# Kairos authentication session policy

## Existing architecture

Kairos uses short-lived signed JWT access tokens in the `Authorization: Bearer` header. The access token is held in per-tab `sessionStorage`; account eligibility and the `accounts.token_version` value are checked by the backend on authenticated requests. Previously, no refresh-token endpoint existed, so a reload in a new tab/browser session required another login.

## Implemented policy

- Access JWT: `ACCESS_TOKEN_EXPIRE_MINUTES`, default **30 minutes**.
- Refresh session: `SESSION_LIFETIME_SECONDS`, default **604800 seconds (7 days)**.
- Session lifetime is **fixed/absolute**, not sliding. Refresh rotates the opaque refresh credential and issues a new access JWT, but does not change the session's original `expires_at`.
- The refresh credential is a random opaque value stored only as a SHA-256 hash in `auth_sessions`; the browser receives it in an HttpOnly cookie named `kairos_refresh`.
- Cookie path is `/api/v1/auth`, SameSite=Lax, and Secure in production/staging. The refresh/logout endpoints reject a supplied Origin that does not match the configured `FRONTEND_URL`.
- Active authenticated API use refreshes an access token when it is within two minutes of expiry. A 401 can also trigger one refresh-and-retry attempt. Refresh calls are deduplicated within a tab and use the Web Locks API to serialize rotation across tabs where supported.
- Logout revokes the user's active sessions and increments `accounts.token_version`, invalidating outstanding access JWTs. If the access token has expired, logout can still revoke the refresh session using the HttpOnly cookie.
- Password reset continues to increment `token_version`; deactivated, unverified, revoked, expired, or version-mismatched accounts/sessions cannot refresh.
- Email verification (`accounts.is_verified`), Aadhaar identity verification (`accounts.identity_verified`), RBAC, and role resolution are not changed by refresh.

## Database setup (manual MySQL SQL)

The ORM model is `backend/app/models/auth_session.py`. Production needs the table before the new login route can create sessions. As requested, no Alembic migration is supplied for this change. Review and execute `docs/sql/20261026_auth_sessions.sql` manually in the intended database after backup and schema verification. Do not run it automatically against production. Existing sessions in the new table are not backfilled; users must sign in once after deployment to create a refresh session.

## Deployment checks

1. Confirm `FRONTEND_URL` exactly matches the browser's frontend origin.
2. Use HTTPS and set `ENVIRONMENT=production` in production so the refresh cookie receives the Secure flag.
3. Execute and validate the manual SQL before deploying the backend.
4. Deploy backend and frontend together; refresh requests use `credentials: include`.
5. Verify login returns a refresh cookie with HttpOnly, Secure in production, SameSite=Lax, and a seven-day Max-Age; verify refresh rotates the cookie without changing the absolute expiry; verify logout and account deactivation prevent refresh.

## Boundaries

A tab remaining open does not extend the seven-day absolute session lifetime. The frontend refreshes during active authenticated API use near access-token expiry; it does not run a background polling loop. Browsers without the Web Locks API retain per-tab refresh deduplication but may be more susceptible to simultaneous cross-tab refresh races. When offline, local logout is immediate, but server-side revocation requires a request to reach the backend; the cookie still has its finite expiry.
