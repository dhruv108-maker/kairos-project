"""User-declared identity details, kept separate from authoritative claims."""
from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IdentityDetails(Base):
    """Optional user-entered name; never evidence that the identity is verified."""

    __tablename__ = "identity_details"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_identity_details_account"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[int | str] = mapped_column(
        MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    declared_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    consented_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    consent_notice_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
