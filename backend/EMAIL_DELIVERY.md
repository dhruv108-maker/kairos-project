# Kairos transactional email delivery

Kairos uses one provider adapter in `backend/app/services/email.py`. Authentication and invitation workflows call the public helpers in this module; do not add SMTP clients or provider SDK calls to route/service modules.

## Configuration

Set these values in the backend process environment or the repository-root `.env.local` file (never commit that file):

- `RESEND_API_KEY`: API key for the Resend project.
- `RESEND_FROM_EMAIL`: sender address verified in Resend. The service adds `MAIL_FROM_NAME` as the display name unless the value already includes one.
- `MAIL_FROM_NAME`: optional sender display name; defaults to `Kairos`.
- `FRONTEND_URL`: trusted frontend origin used to create verification, reset, and invitation links. Do not derive these links from the incoming request host.

Example placeholders are in the root `.env.example`. Do not paste production credentials into source control or logs.

## Existing workflows discovered

| Trigger | Calling code | Delivery helper | Security / failure behavior |
| --- | --- | --- | --- |
| Student registration | `backend/app/api/auth.py` | `send_verification_email` | Verification token hash stored; API indicates whether provider accepted the message. |
| Faculty registration | `backend/app/api/auth.py` | `send_verification_email` | Account remains pending approval; API indicates email availability. |
| Verification resend | `backend/app/api/auth.py` | `send_verification_email` | Generic response avoids account enumeration; token is hashed and expires after 30 minutes. |
| Password reset request | `backend/app/api/auth.py` | `send_password_reset_email` | Generic response; hashed single-use token with 30-minute expiry and account-level cooldown. Failed delivery clears the pending reset token. |
| Institution invitation | `backend/app/modules/institutions/invitation_service.py` | `send_institution_invitation_email` | Token hash stored, seven-day expiry, single-use acceptance; failed delivery revokes invitation. |
| Business workflow notifications | Available helper in `backend/app/services/email.py` | `send_workflow_notification` | Shared delivery path; callers must use only for authorized, established business events. |

The current backend has no separate email OTP delivery/validation workflow, login-alert workflow, or general notification queue identified in the route/service modules. The frontend includes template OTP screens, but a UI screen alone is not evidence of a backend OTP-email feature.

## Delivery semantics and operations

- A successful helper return means Resend accepted the request and returned a provider message ID. It does **not** prove inbox delivery; delivery, bounce, and complaint events require provider webhooks/event ingestion, which are not currently implemented.
- The provider adapter retries selected transient HTTP statuses and network/timeouts up to three total attempts with bounded exponential backoff. Permanent client errors are not retried.
- Logs contain provider message IDs and sanitized error types/statuses, not API credentials, recipient message bodies, OTPs, or raw action tokens.
- Delivery remains synchronous after the account/invitation transaction commits. No queue or outbox has been introduced because the current repository does not establish a queue infrastructure.
- Automated tests should mock HTTP responses. Never test by sending messages to arbitrary users.

## Production setup checklist

1. Create/use a Resend project and store its API key as `RESEND_API_KEY` in the deployment secret store.
2. Verify the sending domain in Resend and configure the exact DNS records Resend provides, including SPF and DKIM. Configure DMARC for the domain according to the organization's email policy.
3. Set `RESEND_FROM_EMAIL` to an address on the verified domain, `MAIL_FROM_NAME=Kairos`, and `FRONTEND_URL` to the canonical HTTPS frontend origin.
4. Restart/redeploy the backend so the environment is loaded.
5. Run the mocked email tests and then perform a controlled integration test with an explicitly authorized test inbox.
6. Confirm provider events/delivery in Resend. Do not mark production email as verified solely because the API returned success.
