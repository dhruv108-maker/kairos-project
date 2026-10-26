"""Server-side Verifico Aadhaar OCR adapter.

OCR output is extraction only. It is never an authoritative identity-verification
decision and must not set an account's identity_verified flag.
"""
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import settings


class IdentityVerificationProvider(Protocol):
    @property
    def is_available(self) -> bool: ...

    @property
    def name(self) -> str: ...

    async def initiate(self, *, account_id: str, consent_notice_version: str, aadhaar_number: str): ...

    async def validate_result(self, *, provider_reference: str, payload: dict) -> bool: ...


class IdentityProviderUnavailable(RuntimeError):
    """Raised when the configured provider cannot safely process a request."""


@dataclass(frozen=True)
class AadhaarOcrResult:
    document_type: str
    fields: dict[str, str | None]
    processing_time_ms: int | None = None


class VerificoAadhaarOcrProvider:
    """Uploads an Aadhaar document to Verifico and returns a minimal OCR projection."""

    name = "verifico_ocr"
    MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "application/pdf": ".pdf",
    }

    @property
    def is_available(self) -> bool:
        key = settings.VERIFICO_API
        return bool(
            key
            and key.get_secret_value().strip()
            and settings.VERIFICO_BASE_URL.startswith("https://")
        )

    async def extract_aadhaar(self, *, filename: str, content_type: str, content: bytes) -> AadhaarOcrResult:
        if not self.is_available:
            raise IdentityProviderUnavailable("Verifico Aadhaar OCR is not configured.")
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValueError("Upload an Aadhaar image in JPG/PNG format or a PDF.")
        if not content or len(content) > self.MAX_DOCUMENT_BYTES:
            raise ValueError("The Aadhaar document must be between 1 byte and 10 MB.")

        # Keep filenames out of logs and send the bytes only to the configured provider.
        safe_name = "aadhaar" + self.ALLOWED_CONTENT_TYPES[content_type]
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=5.0),
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    f"{settings.VERIFICO_BASE_URL.rstrip('/')}/api/v1/documents/extract/aadhaar",
                    headers={"X-API-Key": settings.VERIFICO_API.get_secret_value()},
                    files={"file": (safe_name, content, content_type)},
                )
                if response.status_code in (401, 403):
                    raise IdentityProviderUnavailable("Verifico rejected the configured API key.")
                if response.status_code == 429 or response.status_code >= 500:
                    raise IdentityProviderUnavailable("Verifico Aadhaar OCR is temporarily unavailable.")
                if response.status_code != 200:
                    raise IdentityProviderUnavailable("Verifico could not process this Aadhaar document.")
                body = response.json()
        except (httpx.TimeoutException, httpx.NetworkError):
            raise IdentityProviderUnavailable("Verifico Aadhaar OCR is temporarily unavailable.") from None
        except (ValueError, TypeError):
            raise IdentityProviderUnavailable("Verifico returned an unreadable OCR response.") from None

        if not isinstance(body, dict) or body.get("success") is not True:
            raise IdentityProviderUnavailable("Verifico did not return a successful OCR result.")
        data = body.get("data")
        if not isinstance(data, dict):
            raise IdentityProviderUnavailable("Verifico returned no structured OCR fields.")

        # Allowlist only expected fields. Never return the full Aadhaar number, raw
        # provider payload, base64 photo, QR payload, or arbitrary provider fields.
        aadhaar = self._first_text(data, "aadhaar_number", "aadhaar", "aadhaar_no", "uid", "id_number")
        digits = "".join(char for char in (aadhaar or "") if char.isdigit())
        fields = {
            "name": self._first_text(data, "name", "full_name", "holder_name"),
            "date_of_birth": self._first_text(data, "dob", "date_of_birth", "year_of_birth", "yob"),
            "gender": self._first_text(data, "gender", "sex"),
            "address": self._first_text(data, "address", "full_address"),
            "pin_code": self._first_text(data, "pin_code", "pincode", "postal_code"),
            "state": self._first_text(data, "state"),
            "aadhaar_last4": digits[-4:] if len(digits) >= 4 else None,
        }
        processing = body.get("processing_time_ms")
        return AadhaarOcrResult(
            document_type=str(body.get("document_type") or "aadhaar")[:40],
            fields=fields,
            processing_time_ms=processing if type(processing) is int and processing >= 0 else None,
        )

    @staticmethod
    def _first_text(data: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str):
                cleaned = " ".join(value.split())
                if cleaned:
                    return cleaned[:1000]
        return None

    async def initiate(self, *, account_id: str, consent_notice_version: str, aadhaar_number: str):
        # OCR does not verify Aadhaar identity. This legacy route must fail closed.
        raise IdentityProviderUnavailable(
            "Verifico Aadhaar OCR extracts document fields; it does not verify identity."
        )

    async def validate_result(self, *, provider_reference: str, payload: dict) -> bool:
        raise IdentityProviderUnavailable(
            "Verifico Aadhaar OCR output is not an authoritative identity-verification result."
        )


# Retain the old import name temporarily for compatibility; it no longer calls Signzy.
SignzyAadhaarProvider = VerificoAadhaarOcrProvider
VerificoAadhaarProvider = VerificoAadhaarOcrProvider
