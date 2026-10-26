# Kairos Aadhaar identity verification

## Current behavior

The student profile page includes an authenticated status card backed by
`GET /api/v1/identity-verification/status`. Status is derived from the
server-side `identity_verifications` records associated with the account in
the access token. The initiate endpoint requires explicit consent and a notice
version, but currently returns a safe `503 identity_verification_unavailable`
because the configured provider adapter is intentionally disabled.

The existing model and additive migration store minimal attempt metadata:
account reference, provider reference, normalized status, consent notice
version/timestamp, lifecycle timestamps, and a non-sensitive error category.
The workflow does not accept client-supplied account IDs or verification
success flags. It does not persist Aadhaar numbers, OTPs, or raw documents.

## Provider evidence and blocker

The public TheVerifico Aadhaar OCR page documents
`POST https://api.theverifico.com/api/v1/ocr/aadhaar` with bearer API-key
authentication for **document OCR/extraction**. The same page explicitly says
Aadhaar verification against UIDAI is not offered as a product. OCR output is
not authoritative identity verification, so Kairos must not mark an account
verified from extracted text or a generic HTTP 200.

Sources:
- https://www.theverifico.com/aadhaar-ocr-api
- https://www.theverifico.com/

No provider request is made by the current Kairos identity-verification
adapter, and no credential was inspected or printed during this work.
The old `VERIFICO_API` example variable is ambiguous and unused. It is
retained as a documented historical name only; do not configure it expecting
the current identity workflow to become active.

## Required before enabling a live workflow

1. Obtain written provider confirmation of an approved Aadhaar identity
   verification product, its supported API contract, allowed use, and retention
   terms. If the intent is Aadhaar authentication rather than OCR, use an
   appropriately authorised ecosystem/provider route and complete applicable
   legal, contractual, consent, and security reviews.
2. Confirm server-side credential name and authentication mechanism from that
   contract; store the credential only in server environment/secret management.
3. Implement the documented transaction lifecycle, provider result validation,
   idempotency/replay protection, bounded timeouts/rate handling, and callback
   signature validation or supported status polling.
4. Test against provider sandbox credentials and then separately verify a real
   authorised request. Do not use real Aadhaar numbers or OTPs in CI.
5. Define purpose limitation, notice/consent, retention, and deletion policy
   before collecting any identity document or Aadhaar data.

No database migration was required for the status-only UI integration.
