from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP, UniqueConstraint, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SavedJob(Base):
    """A student's saved native Kairos opportunity."""

    __tablename__ = "saved_jobs"
    __table_args__ = (
        UniqueConstraint("account_id", "opportunity_id", name="uq_saved_job_account_opportunity"),
        Index("ix_saved_jobs_account_created", "account_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("internship_opportunities.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
