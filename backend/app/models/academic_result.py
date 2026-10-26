"""Approved grading policies and canonical published internship results."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class InternshipGradingPolicy(Base):
    __tablename__ = "internship_grading_policies"
    __table_args__ = (UniqueConstraint("institution_id", "version_number", name="uq_internship_policy_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="DRAFT")
    policy_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_account_id: Mapped[int | str] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    approved_by_account_id: Mapped[int | str | None] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class OfficialInternshipResult(Base):
    __tablename__ = "official_internship_results"
    __table_args__ = (UniqueConstraint("report_submission_id", name="uq_official_result_submission"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_submission_id: Mapped[str] = mapped_column(ForeignKey("report_submissions.id", ondelete="RESTRICT"), nullable=False)
    report_version_id: Mapped[str] = mapped_column(ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False)
    placement_id: Mapped[str] = mapped_column(ForeignKey("internship_placements.id", ondelete="RESTRICT"), nullable=False)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True)
    academic_year_id: Mapped[str | None] = mapped_column(ForeignKey("academic_years.id", ondelete="SET NULL"))
    semester_number: Mapped[int | None] = mapped_column(Integer)
    curriculum_mapping_version_id: Mapped[str | None] = mapped_column(ForeignKey("curriculum_mapping_versions.id", ondelete="SET NULL"))
    grading_policy_id: Mapped[str] = mapped_column(ForeignKey("internship_grading_policies.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="AWAITING_APPROVAL")
    total_score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    final_grade: Mapped[str | None] = mapped_column(String(20))
    created_by_account_id: Mapped[int | str] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    approved_by_account_id: Mapped[int | str | None] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    published_by_account_id: Mapped[int | str | None] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="SET NULL"))
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class OfficialInternshipResultHistory(Base):
    __tablename__ = "official_internship_result_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    result_id: Mapped[str] = mapped_column(ForeignKey("official_internship_results.id", ondelete="RESTRICT"), nullable=False, index=True)
    actor_account_id: Mapped[int | str] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_values: Mapped[dict | None] = mapped_column(JSON)
    new_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
