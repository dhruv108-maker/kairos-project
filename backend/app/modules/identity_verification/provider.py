"""Provider boundary for Aadhaar identity verification.

TheVerifico's currently published documentation describes Aadhaar OCR/extraction,
not an Aadhaar identity-verification transaction. OCR output is not proof of identity.
This adapter therefore fails closed until the provider supplies a documented,
authorised Aadhaar verification flow and credentials enabled for that product.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class IdentityProviderUnavailable(RuntimeError):
    """Raised when no supported, configured verification flow is available."""


@dataclass(frozen=True)
class VerificationStart:
    provider_reference: str
    redirect_url: str | None
    expires_at: datetime | None = None


class IdentityVerificationProvider(Protocol):
    """Contract implemented by a provider with a documented verification flow."""

    async def initiate(
        self, *, account_id: str, consent_notice_version: str
    ) -> VerificationStart: ...

    async def validate_result(
        self, *, provider_reference: str, payload: dict
    ) -> bool: ...


class VerificoAadhaarProvider:
    """Mockable provider contract; deliberately does not mistake OCR for verification."""

    async def initiate(
        self, *, account_id: str, consent_notice_version: str
    ) -> VerificationStart:
        raise IdentityProviderUnavailable(
            "TheVerifico currently documents Aadhaar OCR extraction only; a supported "
            "Aadhaar identity-verification flow has not been documented/configured."
        )

    async def validate_result(self, *, provider_reference: str, payload: dict) -> bool:
        # No callback/result-validation mechanism is documented for Aadhaar verification.
        # Never accept a client-supplied success flag.
        raise IdentityProviderUnavailable(
            "A trustworthy Verifico Aadhaar verification result cannot currently be validated."
        )
