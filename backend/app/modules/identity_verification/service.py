"""Identity workflow: OCR is not an authoritative identity verification result."""
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Account
from app.models.identity_verification import IdentityVerification
from app.models.identity_details import IdentityDetails
from app.modules.identity_verification.provider import (
    IdentityProviderUnavailable,
    IdentityVerificationProvider,
    VerificoAadhaarOcrProvider,
)


class IdentityVerificationService:
    def __init__(self, db: AsyncSession, provider: IdentityVerificationProvider | None = None):
        self.db = db
        self.provider = provider or VerificoAadhaarOcrProvider()

    async def status(self, account_id: str | int) -> dict:
        account = await self.db.scalar(select(Account).where(Account.id == account_id).with_for_update())
        if account is None:
            raise ValueError("Authenticated account no longer exists")
        latest = await self.db.scalar(
            select(IdentityVerification).where(IdentityVerification.account_id == account_id)
            .order_by(IdentityVerification.created_at.desc(), IdentityVerification.id.desc()).limit(1)
        )
        details = await self.db.scalar(select(IdentityDetails).where(IdentityDetails.account_id == account_id).limit(1))
        if account.identity_verified and (
            latest is None
            or latest.status != "verified"
            or latest.provider in {"signzy", "verifico", "verifico_ocr"}
        ):
            account.identity_verified = False
            await self.db.commit()
            await self.db.refresh(account)
        identity_verified = bool(
            account.identity_verified
            and latest is not None
            and latest.status == "verified"
            and latest.provider not in {"signzy", "verifico", "verifico_ocr"}
        )
        if latest is None:
            state = "not_started"
        elif latest.status == "verified" and not identity_verified:
            state = "review_required"
        else:
            state = latest.status
        ocr_available = bool(getattr(self.provider, "is_available", False))
        result = {
            "status": state,
            "identity_verification_status": state,
            "verified": identity_verified,
            "identity_verified": identity_verified,
            "email_verified": bool(account.is_verified),
            # OCR availability is separate from identity-verification availability.
            "available": False,
            "ocr_available": ocr_available,
            "provider": latest.provider if latest else getattr(self.provider, "name", "verifico_ocr"),
            "message": (
                "OCR extracts document fields only; identity remains unverified until a separate authoritative verification is completed."
                if not identity_verified
                else None
            ),
            "declared_name": details.declared_name if details else None,
        }
        if latest is not None:
            result.update({
                "id": latest.id, "created_at": latest.created_at, "updated_at": latest.updated_at,
                "expires_at": latest.expires_at, "completed_at": latest.completed_at,
                "error_category": latest.error_category,
            })
        return result

    async def initiate(
        self, account_id: str | int, consent: bool, notice_version: str, aadhaar_number: str
    ) -> dict:
        if not consent:
            raise ValueError("Explicit consent is required before initiating identity verification.")
        version = notice_version.strip()
        if not version or len(version) > 40:
            raise ValueError("A valid consent notice version is required.")
        if len(aadhaar_number) != 12 or not aadhaar_number.isascii() or not aadhaar_number.isdigit():
            raise ValueError("Enter a valid 12-digit Aadhaar number.")
        raise IdentityProviderUnavailable(
            "Verifico Aadhaar OCR does not verify Aadhaar identity. Upload a document for OCR extraction only."
        )

    async def apply_authoritative_result(self, *, account_id: str | int, provider_reference: str, payload: dict) -> dict:
        """Apply a result only after trusted provider validation; OCR cannot complete this flow."""
        account = await self.db.scalar(select(Account).where(Account.id == account_id).with_for_update())
        if account is None:
            raise ValueError("Account not found")
        record = await self.db.scalar(select(IdentityVerification).where(
            IdentityVerification.account_id == account_id,
            IdentityVerification.provider_reference == provider_reference,
        ).with_for_update())
        if record is None:
            raise ValueError("Identity verification attempt not found")
        if record.status in {"failed", "expired", "cancelled", "review_required"}:
            raise ValueError("This identity verification attempt is no longer eligible for completion.")
        try:
            validated = await self.provider.validate_result(provider_reference=provider_reference, payload=payload)
        except (IdentityProviderUnavailable, asyncio.TimeoutError):
            raise IdentityProviderUnavailable("An authoritative identity result cannot currently be validated.") from None
        if validated is not True:
            raise IdentityProviderUnavailable("The provider did not validate an authoritative successful identity result.")
        now = datetime.now(UTC).replace(tzinfo=None)
        record.status = "verified"
        record.completed_at = now
        record.error_category = None
        account.identity_verified = True
        await self.db.commit()
        await self.db.refresh(record)
        await self.db.refresh(account)
        return {"status": "verified", "identity_verification_status": "verified", "verified": True,
                "identity_verified": True, "email_verified": bool(account.is_verified), "completed_at": record.completed_at}

    async def save_details(self, account_id: str | int, declared_name: str | None, consent: bool, notice_version: str) -> dict:
        """Save user-declared details only; never changes verification status."""
        if not consent:
            raise ValueError("Explicit consent is required to store optional identity details.")
        version = notice_version.strip()
        if not version or len(version) > 40:
            raise ValueError("A valid consent notice version is required.")
        name = declared_name.strip() if declared_name is not None else None
        if name == "":
            name = None
        if name is not None and (len(name) > 200 or any(ord(char) < 32 for char in name)):
            raise ValueError("The declared name must be 1-200 printable characters.")
        details = await self.db.scalar(select(IdentityDetails).where(IdentityDetails.account_id == account_id).limit(1))
        now = datetime.now(UTC).replace(tzinfo=None)
        if details is None:
            details = IdentityDetails(id=str(uuid4()), account_id=account_id, declared_name=name,
                                      consented_at=now, consent_notice_version=version)
            self.db.add(details)
        else:
            details.declared_name = name
            details.consented_at = now
            details.consent_notice_version = version
        await self.db.commit()
        await self.db.refresh(details)
        return {"declared_name": details.declared_name, "consented_at": details.consented_at, "updated_at": details.updated_at}
