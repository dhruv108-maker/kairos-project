"""Versioned rubrics and isolated blind-assessment records."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AssessmentRubric(Base):
    __tablename__ = "assessment_rubrics"
    __table_args__ = (UniqueConstraint("institution_id", "name", "version_number", name="uq_assessment_rubric_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="DRAFT")
    created_by_account_id: Mapped[int | str] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    approved_by_account_id: Mapped[int | str | None] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class AssessmentRubricCriterion(Base):
    __tablename__ = "assessment_rubric_criteria"
    __table_args__ = (UniqueConstraint("rubric_id", "code", name="uq_rubric_criterion_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    rubric_id: Mapped[str] = mapped_column(ForeignKey("assessment_rubrics.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    minimum_score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    maximum_score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class BlindAssessmentAssignment(Base):
    __tablename__ = "blind_assessment_assignments"
    __table_args__ = (UniqueConstraint("report_version_id", "evaluator_account_id", name="uq_blind_evaluator_per_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_version_id: Mapped[str] = mapped_column(ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    rubric_id: Mapped[str] = mapped_column(ForeignKey("assessment_rubrics.id", ondelete="RESTRICT"), nullable=False)
    evaluator_account_id: Mapped[int | str] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by_account_id: Mapped[int | str] = mapped_column(MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="DRAFT")
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    released_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class BlindAssessmentScore(Base):
    __tablename__ = "blind_assessment_scores"
    __table_args__ = (UniqueConstraint("assignment_id", "criterion_id", name="uq_blind_score_criterion"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("blind_assessment_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_id: Mapped[str] = mapped_column(ForeignKey("assessment_rubric_criteria.id", ondelete="RESTRICT"), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
