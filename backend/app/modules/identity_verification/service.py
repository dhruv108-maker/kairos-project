"""Authenticated account identity-verification workflow."""
import asyncio
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity_verification import IdentityVerification
from app.modules.identity_verification.provider import (
    IdentityProviderUnavailable,
    IdentityVerificationProvider,
    VerificoAadhaarProvider,
)


class IdentityVerificationService:
    def __init__(
        self,
        db: AsyncSession,
        provider: IdentityVerificationProvider | None = None,
    ):
        self.db = db
        self.provider = provider or VerificoAadhaarProvider()

    async def status(self, account_id: str) -> dict:
        latest = await self.db.scalar(
            select(IdentityVerification)
            .where(IdentityVerification.account_id == account_id)
            .order_by(IdentityVerification.created_at.desc())
            .limit(1)
        )
        if latest is None:
            return {
                "status": "not_started",
                "verified": False,
                "available": False,
                "provider": "verifico",
                "message": "Optional Aadhaar verification is not currently available.",
            }
        return {
            "id": latest.id,
            "status": latest.status,
            "verified": latest.status == "verified",
            "available": False,
            "provider": latest.provider,
            "created_at": latest.created_at,
            "updated_at": latest.updated_at,
            "expires_at": latest.expires_at,
            "completed_at": latest.completed_at,
            "error_category": latest.error_category,
        }

    async def initiate(
        self, account_id: str, consent: bool, notice_version: str
    ) -> dict:
        if not consent:
            raise ValueError(
                "Explicit consent is required before initiating identity verification."
            )
        normalized_notice_version = notice_version.strip()
        if not normalized_notice_version or len(normalized_notice_version) > 40:
            raise ValueError("A valid consent notice version is required.")

        # No database record is created until the provider confirms that a real transaction
        # was created. This avoids showing a false pending state when the provider is unsupported.
        try:
            started = await self.provider.initiate(
                account_id=account_id,
                consent_notice_version=normalized_notice_version,
            )
        except (IdentityProviderUnavailable, asyncio.TimeoutError):
            # Fail closed and let the API return a stable, non-sensitive unavailable response.
            raise IdentityProviderUnavailable(
                "Identity verification is currently unavailable."
            ) from None

        # Validate provider initiation metadata before storing a pending attempt. This is
        # not verification success; it only guards the local record from malformed adapter data.
        if not isinstance(started.provider_reference, str):
            raise IdentityProviderUnavailable("The provider returned an invalid transaction reference.")
        provider_reference = started.provider_reference.strip()
        if not provider_reference or len(provider_reference) > 255:
            raise IdentityProviderUnavailable(
                "The provider returned an invalid transaction reference."
            )
        if started.redirect_url is not None:
            if not isinstance(started.redirect_url, str):
                raise IdentityProviderUnavailable("The provider returned an invalid verification redirect.")
            try:
                redirect = urlsplit(started.redirect_url)
                valid_redirect = (
                    redirect.scheme == "https"
                    and bool(redirect.hostname)
                    and redirect.username is None
                    and redirect.password is None
                )
            except ValueError:
                valid_redirect = False
            if not valid_redirect:
                raise IdentityProviderUnavailable(
                    "The provider returned an invalid verification redirect."
                )

        now = datetime.now(UTC).replace(tzinfo=None)
        record = IdentityVerification(
            id=str(uuid4()),
            account_id=account_id,
            provider="verifico",
            provider_reference=provider_reference,
            status="pending",
            consented_at=now,
            consent_notice_version=normalized_notice_version,
            expires_at=started.expires_at,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return {
            "id": record.id,
            "status": record.status,
            "redirect_url": started.redirect_url,
            "expires_at": record.expires_at,
        }
