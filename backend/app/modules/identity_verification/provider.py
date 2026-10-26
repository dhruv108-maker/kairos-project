"""Server-side Signzy Aadhaar verification adapter.

This adapter calls Signzy's India identity API. It is disabled by default and
fails closed unless explicitly enabled with private deployment credentials.
It never logs, persists, or returns the Aadhaar number or raw provider payload.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

import httpx

from app.core.config import settings


class IdentityProviderUnavailable(RuntimeError):
    """Raised when the approved/configured provider cannot safely verify identity."""


@dataclass(frozen=True)
class VerificationStart:
    provider_reference: str
    redirect_url: str | None
    expires_at: datetime | None = None
    verified: bool | None = None
    message: str | None = None


class IdentityVerificationProvider(Protocol):
    @property
    def is_available(self) -> bool: ...

    @property
    def name(self) -> str: ...

    async def initiate(
        self, *, account_id: str, consent_notice_version: str, aadhaar_number: str
    ) -> VerificationStart: ...

    async def validate_result(self, *, provider_reference: str, payload: dict) -> bool: ...


class SignzyAadhaarProvider:
    """Signzy Aadhaar-number verification; credentials remain server-side."""

    @property
    def name(self) -> str:
        return "signzy"

    @property
    def is_available(self) -> bool:
        return bool(
            settings.SIGNZY_AADHAAR_ENABLED
            and settings.SIGNZY_USERNAME
            and settings.SIGNZY_PASSWORD
            and settings.SIGNZY_USERNAME.get_secret_value().strip()
            and settings.SIGNZY_PASSWORD.get_secret_value().strip()
            and settings.SIGNZY_BASE_URL.startswith("https://")
        )

    async def initiate(
        self, *, account_id: str, consent_notice_version: str, aadhaar_number: str
    ) -> VerificationStart:
        # Do not call external systems unless the deployment owner explicitly enabled
        # the product and supplied credentials from a private secret store.
        if not self.is_available:
            raise IdentityProviderUnavailable(
                "Signzy Aadhaar verification is not enabled or configured for this deployment."
            )
        if len(aadhaar_number) != 12 or not aadhaar_number.isascii() or not aadhaar_number.isdigit():
            raise ValueError("Enter a valid 12-digit Aadhaar number.")

        base_url = settings.SIGNZY_BASE_URL.rstrip("/")
        timeout = httpx.Timeout(15.0, connect=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                login = await client.post(
                    f"{base_url}/api/customers/login",
                    json={
                        "username": settings.SIGNZY_USERNAME.get_secret_value(),
                        "password": settings.SIGNZY_PASSWORD.get_secret_value(),
                    },
                    headers={"Content-Type": "application/json"},
                )
                if login.status_code != 200:
                    raise IdentityProviderUnavailable("Signzy authentication failed.")
                login_body = login.json()
                access_token = login_body.get("id") if isinstance(login_body, dict) else None
                if not isinstance(access_token, str) or not access_token.strip():
                    raise IdentityProviderUnavailable("Signzy returned an invalid access token.")

                response = await client.post(
                    f"{base_url}/api/v3/aadhaar/verify",
                    headers={
                        "Authorization": access_token,
                        "Content-Type": "application/json",
                    },
                    json={"aadhaarNumber": aadhaar_number, "consent": "Y"},
                )
                if response.status_code in (401, 403):
                    raise IdentityProviderUnavailable("Signzy rejected the configured credentials.")
                if response.status_code == 422:
                    raise IdentityProviderUnavailable("The provider rejected the Aadhaar verification request.")
                if response.status_code >= 500:
                    raise IdentityProviderUnavailable("Signzy Aadhaar verification is temporarily unavailable.")
                if response.status_code != 200:
                    raise IdentityProviderUnavailable("Signzy returned an unexpected verification response.")
                body = response.json()
        except (httpx.TimeoutException, httpx.NetworkError):
            raise IdentityProviderUnavailable("Signzy Aadhaar verification is temporarily unavailable.") from None
        except (ValueError, TypeError):
            # JSON parsing and unexpected provider response shapes must never count as success.
            raise IdentityProviderUnavailable("Signzy returned an unreadable verification response.") from None

        if not isinstance(body, dict):
            raise IdentityProviderUnavailable("Signzy returned an invalid verification response.")
        result = body.get("result")
        if not isinstance(result, dict):
            raise IdentityProviderUnavailable("Signzy returned no structured verification result.")

        # Only explicit boolean decision fields count. HTTP 200 or a generic API
        # status such as "success" is not enough to establish identity.
        decision = next(
            (result[key] for key in ("verified", "validated", "valid") if type(result.get(key)) is bool),
            None,
        )
        if decision is None:
            raise IdentityProviderUnavailable(
                "Signzy's response did not contain an explicit identity verification decision."
            )

        reference = next(
            (
                str(value).strip()
                for value in (
                    body.get("requestId"),
                    body.get("transactionId"),
                    result.get("referenceId"),
                    result.get("reference_id"),
                )
                if isinstance(value, (str, int)) and str(value).strip()
            ),
            f"signzy-{uuid4()}",
        )
        # Store only a provider reference and the boolean decision, never provider PII.
        return VerificationStart(
            provider_reference=reference[:255],
            redirect_url=None,
            verified=decision,
            message="Provider verification completed." if decision else "Provider could not verify the submitted Aadhaar details.",
        )

    async def validate_result(self, *, provider_reference: str, payload: dict) -> bool:
        # This product returns a synchronous result; client-supplied callbacks are not trusted.
        raise IdentityProviderUnavailable("Client-supplied verification results are not accepted.")


# Backwards-compatible import alias while callers/tests migrate to the real adapter.
VerificoAadhaarProvider = SignzyAadhaarProvider
