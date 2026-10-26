"""Versioned curriculum outcomes and report evidence mappings."""
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class LearningOutcome(Base):
    __tablename__ = "learning_outcomes"
    __table_args__ = (UniqueConstraint("institution_id", "programme_id", "code", name="uq_learning_outcome_scope_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    programme_id: Mapped[str | None] = mapped_column(ForeignKey("programmes.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class CurriculumMappingVersion(Base):
    __tablename__ = "curriculum_mapping_versions"
    __table_args__ = (UniqueConstraint("report_version_id", "version_number", name="uq_curriculum_mapping_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_version_id: Mapped[str] = mapped_column(ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="SUBMITTED")
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    created_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class CurriculumMappingItem(Base):
    __tablename__ = "curriculum_mapping_items"
    __table_args__ = (UniqueConstraint("mapping_version_id", "learning_outcome_id", name="uq_mapping_outcome"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mapping_version_id: Mapped[str] = mapped_column(ForeignKey("curriculum_mapping_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_outcome_id: Mapped[str] = mapped_column(ForeignKey("learning_outcomes.id", ondelete="RESTRICT"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_file_id: Mapped[str] = mapped_column(ForeignKey("storage_files.id", ondelete="RESTRICT"), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="UNREVIEWED")
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(String(40), nullable=False, server_default="FACULTY_OR_STUDENT_MAPPING")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
