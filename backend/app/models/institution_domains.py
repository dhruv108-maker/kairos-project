from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InstitutionDomain(Base):
    """A domain explicitly verified by Kairos administrators for an institution."""

    __tablename__ = "institution_domains"
    __table_args__ = (
        UniqueConstraint("normalized_domain", name="uq_institution_domains_domain"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    normalized_domain: Mapped[str] = mapped_column(String(253), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now()
    )
