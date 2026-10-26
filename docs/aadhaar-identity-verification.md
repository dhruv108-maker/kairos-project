# Verifico Aadhaar OCR integration

## What this integration does

Kairos calls Verifico's Aadhaar document extraction endpoint from the backend. The authenticated student uploads a JPG, PNG, or PDF (maximum 10 MB) after explicit consent. Kairos forwards it to Verifico, returns a minimal allowlisted set of extracted fields to that same student, masks the Aadhaar number to its last four digits, and does not persist the upload or raw OCR response.

This is OCR only. It is not UIDAI Aadhaar authentication, OTP possession verification, or proof that the person presenting the document is its holder. OCR never sets accounts.identity_verified, creates a verified identity-verification attempt, or changes accounts.is_verified (email verification). Identity remains unverified until a separate authoritative verification workflow is implemented and completed.

## Provider contract

- Base URL: https://api.theverifico.com
- Endpoint: POST /api/v1/documents/extract/aadhaar
- Authentication: X-API-Key header
- Upload: multipart/form-data field named file
- Supported types in Kairos: image/jpeg, image/png, application/pdf
- Maximum upload: 10 MB
- API key remains server-side and is stored as a Pydantic SecretStr.

Reference: https://www.theverifico.com/blog/ocr-to-verification-workflow-for-indian-documents and https://www.theverifico.com/aadhaar-ocr-api. The provider's published docs distinguish Aadhaar OCR from identity verification and say Aadhaar identity verification is not offered as a product.

## Environment

Set the key in the backend repository root .env.local or deployment secret manager, not in frontend environment variables:

    verifico_api=YOUR_PRIVATE_VERIFICO_API_KEY
    VERIFICO_BASE_URL=https://api.theverifico.com

Kairos uses case-insensitive environment settings, so the existing lowercase verifico_api key is accepted as VERIFICO_API. Do not commit .env.local or paste the key into chat. If the key was ever committed or exposed, rotate it with Verifico.

## API

Authenticated request:

    POST /api/v1/identity-verification/ocr
    Content-Type: multipart/form-data
    file=<document>
    consent=true

Response contains an allowlisted field projection, processing time, and identity_verified=false. Full Aadhaar numbers, raw provider payloads, base64 photos, and QR payloads are not returned or stored. Client-supplied identity result fields are not accepted as verification evidence.

## Privacy and security

- Explicit consent is required on each upload.
- Only authenticated accounts can call the endpoint.
- Provider calls use HTTPS and do not follow redirects.
- Upload size and content type are validated; request memory is bounded.
- The uploaded file and raw provider response are not written to Kairos storage or logs.
- Extracted fields are returned to the requesting student only and are not persisted in the database.
- Provider errors fail closed and never produce a verified state.
- The frontend clears the selected file after each attempt and never sees the API key.

Before production, review Verifico's data-processing terms, retention policy, contractual authorization and the institution's lawful basis for processing Aadhaar-related data. Do not call OCR output “verified”.
