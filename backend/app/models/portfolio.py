from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text,
    TIMESTAMP, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StudentAcademicRecord(Base):
    __tablename__ = "student_academic_records"
    __table_args__ = (
        CheckConstraint("grade_value IS NULL OR grade_value >= 0", name="ck_academic_grade_nonnegative"),
        CheckConstraint("grade_max IS NULL OR grade_max > 0", name="ck_academic_grade_max_positive"),
        CheckConstraint("grade_value IS NULL OR grade_max IS NULL OR grade_value <= grade_max", name="ck_academic_grade_within_max"),
        Index("ix_student_academic_records_owner_dates", "student_profile_id", "start_date", "end_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_profile_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualification: Mapped[str] = mapped_column(String(255), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    semester: Mapped[str | None] = mapped_column(String(32))
    grade_value: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    grade_max: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    grading_scale: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    verified_by_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class StudentPortfolioEntry(Base):
    __tablename__ = "student_portfolio_entries"
    __table_args__ = (
        CheckConstraint("kind IN ('skill','project','certification','experience','research','award','achievement','activity')", name="ck_portfolio_entry_kind"),
        Index("ix_portfolio_entries_owner_kind", "student_profile_id", "kind"),
        Index("ix_portfolio_entries_owner_dates", "student_profile_id", "start_date", "end_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_profile_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(2048))
    credential_id: Mapped[str | None] = mapped_column(String(255))
    proficiency: Mapped[str | None] = mapped_column(String(64))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    issued_date: Mapped[date | None] = mapped_column(Date)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    verified_by_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class StudentResume(Base):
    __tablename__ = "student_resumes"
    __table_args__ = (UniqueConstraint("student_profile_id", "storage_file_id", name="uq_student_resume_storage"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_profile_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_file_id: Mapped[str] = mapped_column(ForeignKey("storage_files.id", ondelete="RESTRICT"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
