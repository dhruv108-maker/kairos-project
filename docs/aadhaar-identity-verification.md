# Optional Aadhaar identity details and verification

## Current behavior

Aadhaar-related functionality is optional and does not alter registration, login, account eligibility, academic standing, role assignments, or the existing `accounts.is_verified` field. Authentication continues to use that existing field for its established account-verification purpose. Identity status is a separate claim derived from the latest canonical `identity_verifications` record; no record means `not_started` and `verified: false`.

The student profile allows the user to save an optional, user-declared name at `PUT /api/v1/identity-verification/details`. The current user's account ID is always taken from the authenticated token. The request requires explicit consent and a consent notice version; unknown fields are rejected. The declared name is not an authoritative identity claim and never changes verification status. The status endpoint returns only this name and the minimal verification metadata needed by the signed-in user.

## Persisted data

- `identity_details`: one row per account, with UUID-style row ID, account foreign key, optional `declared_name`, consent timestamp/version, and created/updated timestamps. The unique account constraint implements the one-details-record-per-account rule; account deletion cascades to this row.
- Existing `identity_verifications`: existing attempt metadata, provider reference, state, consent metadata, and lifecycle timestamps remain the canonical verification history. Existing records are not rewritten by this migration.
- No Aadhaar number, masked Aadhaar number, OTP, document image, OCR fields, raw provider payload, or plaintext/hash-based Aadhaar identifier is retained.
- No account-level identity flag is added. The identity-verified state is derived from the canonical verification record, preventing drift between a duplicated account flag and attempt state.

For manual database administration, use [`backend/sql/manual_mysql_identity_details.sql`](../blob/release-v1/backend/sql/manual_mysql_identity_details.sql). It includes read-only pre-checks, an idempotent `CREATE TABLE IF NOT EXISTS` for the optional details table, validation queries, and a commented destructive rollback. It creates no account or verification backfill. No Alembic migration was created, edited, or applied as part of this manual-SQL finalisation. The repository still contains the earlier committed `20261026_37_optional_identity_details.py`; do not run both paths as a new schema change. Review actual database schema first, because the checked-in identity-verification migration uses a `VARCHAR(36)` account key while the Account model declares `BIGINT UNSIGNED`; the SQL file flags this mismatch for DBA review rather than guessing an ALTER.

## State and trust boundary

Supported stored attempt statuses remain `pending`, `verified`, `failed`, `expired`, `cancelled`, and `review_required`; the API also returns `not_started` when no attempt exists. Only a trusted provider integration may write an authoritative result. User-entered details, client callbacks, OCR output, HTTP 200 responses, and client-supplied `verified` fields are not verification evidence. The API rejects unknown request fields and does not expose a client mutation for verification status.

TheVerifico's currently documented Aadhaar capability is OCR/extraction, not authoritative Aadhaar authentication. Its adapter therefore fails closed; initiating verification returns a stable unavailable response and does not create a fake pending attempt. The UI explains the blocker and offers retry/refresh without restricting normal Kairos use.

## Requirements before enabling live verification

Select a provider with an approved, documented Aadhaar authentication flow and contract; confirm legal basis, user-facing consent notice, data-processing/retention terms, and required authorizations. Then implement and test authenticated provider callbacks or server-to-server status retrieval, replay protection, idempotent transaction updates, and an audited atomic transition to `verified` only after the provider's authoritative success semantics are validated. Do not wire the OCR endpoint into this path. No live provider requests or production migration were run for this change.


## Regression coverage

The identity API tests cover authenticated status reads, consent-gated optional-name persistence, normalization, rejection of client-forged identity/verification fields, and unauthenticated mutation rejection. Provider-boundary tests cover the disabled OCR-only adapter, consent gating, malformed provider metadata, unsafe redirects, timeout handling, and the invariant that a client-supplied success payload cannot be validated as an authoritative result.

The repository's GitHub Actions regression workflow must pass on the final commit before this change should be considered verified. The migration has not been applied to a production database; upgrade/downgrade validation must run against the project's isolated database target.


## Separate email and identity verification states

- `accounts.is_verified` remains the email-verification flag used by login/authentication.
- `accounts.identity_verified` is a separate, non-null, default-false summary for authoritative identity verification.
- `identity_verifications` remains the canonical lifecycle record. A summary flag is true only after the backend validates an authoritative provider result and atomically updates both records.
- The status API returns explicit `email_verified`, `identity_verified`, and `identity_verification_status` fields. The legacy `verified` status field remains an identity-only compatibility alias; `accounts.is_verified` is not reinterpreted.
- The current TheVerifico adapter fails closed because OCR/extraction is not authoritative identity authentication. No production verification result is fabricated and the identity flag remains false without an approved provider.
- A legacy lifecycle row marked `verified` without the dedicated account summary is exposed as `review_required`; it is not automatically trusted or backfilled.

### Manual rollout

1. Review and manually execute `backend/sql/manual_mysql_identity_verification.sql` against the intended database after checking the engine/version and existing column definition.
2. Verify the column is `BOOLEAN/TINYINT(1) NOT NULL DEFAULT 0`, and that existing `is_verified` values are unchanged.
3. Deploy the backend model/API changes only after the SQL is complete. Deploy the frontend with the backend.
4. Run the backend regression suite and frontend build/tests. Do not apply an Alembic migration for this column.

The SQL file has not been executed against production. A future provider integration must authenticate its callback and validate an authoritative result before calling the backend service helper. No client-facing endpoint may accept a `verified=true` flag.
