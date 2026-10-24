"""Minimal, privacy-preserving identity-verification attempt metadata."""
from datetime import datetime
from sqlalchemy import CheckConstraint, ForeignKey, Index, String, TIMESTAMP, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class IdentityVerification(Base):
    __tablename__ = "identity_verifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'verified', 'failed', 'expired', 'cancelled', 'review_required')",
            name="identity_verification_status",
        ),
        Index("ix_identity_verifications_account_created", "account_id", "created_at"),
        Index("ix_identity_verifications_status_expiry", "status", "expires_at"),
        UniqueConstraint("provider_reference", name="uq_identity_verifications_provider_reference"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="verifico")
    provider_reference: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    consented_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    consent_notice_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    error_category: Mapped[str | None] = mapped_column(String(80))
    result_metadata: Mapped[str | None] = mapped_column(Text)
