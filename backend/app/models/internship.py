from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Index, BigInteger, Boolean, Date, TIMESTAMP, ForeignKey, Numeric, String, Text, Enum, func, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class InternshipProvider(Base):
    __tablename__ = "internship_providers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255))
    industry_sector: Mapped[str | None] = mapped_column(String(100))
    contact_person_name: Mapped[str | None] = mapped_column(String(150))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    employer_organization_id: Mapped[str | None] = mapped_column(ForeignKey("employer_organizations.id", ondelete="SET NULL"), unique=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class InternshipOpportunity(Base):
    __tablename__ = "internship_opportunities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("internship_providers.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    stipend_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default="0.00")
    application_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    summary: Mapped[str | None] = mapped_column(String(500))
    lifecycle_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="DRAFT", index=True)
    opportunity_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="INTERNSHIP")
    employment_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="INTERNSHIP")
    work_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ONSITE")
    department: Mapped[str | None] = mapped_column(String(120))
    experience_min_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    experience_max_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    compensation_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    compensation_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    compensation_currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    compensation_period: Mapped[str] = mapped_column(String(20), nullable=False, server_default="YEAR")
    compensation_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    openings: Mapped[int] = mapped_column(default=1, nullable=False, server_default="1")
    required_skills: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    preferred_skills: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    education_requirements: Mapped[str | None] = mapped_column(String(2000))
    public_application_url: Mapped[str | None] = mapped_column(String(2048))
    created_by_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class InternshipApplication(Base):
    __tablename__ = "internship_applications"
    __table_args__ = (UniqueConstraint("opportunity_id", "student_id", name="uq_student_opportunity"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("internship_opportunities.id", ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Enum("APPLIED", "SHORTLISTED", "OFFERED", "REJECTED", "WITHDRAWN", name="internship_application_status"), nullable=False, server_default="APPLIED")
    recruitment_stage: Mapped[str] = mapped_column(String(20), nullable=False, server_default="SUBMITTED", index=True)
    applied_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class InternshipPlacement(Base):
    __tablename__ = "internship_placements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("internship_applications.id", ondelete="RESTRICT"), unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False)
    faculty_supervisor_id: Mapped[str | None] = mapped_column(ForeignKey("faculty_profiles.id", ondelete="SET NULL"))
    industry_mentor_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(Enum("ONGOING", "COMPLETED", "TERMINATED", name="internship_placement_status"), nullable=False, server_default="ONGOING")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class RecruitmentStageEvent(Base):
    __tablename__ = "recruitment_stage_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("internship_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    from_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class RecruitmentNote(Base):
    __tablename__ = "recruitment_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("internship_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    author_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class InternshipWorkLog(Base):
    """Student-authored work log for an existing persisted internship placement."""
    __tablename__ = "internship_daily_logs"
    __table_args__ = (
        Index("ix_internship_work_logs_placement_date", "placement_id", "work_date"),
        Index("ix_internship_work_logs_student_status", "student_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    placement_id: Mapped[str] = mapped_column(ForeignKey("internship_placements.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    tasks_completed: Mapped[str] = mapped_column(Text, nullable=False)
    skills_used: Mapped[str | None] = mapped_column(Text)
    challenges: Mapped[str | None] = mapped_column(Text)
    learning_outcomes: Mapped[str | None] = mapped_column(Text)
    next_steps: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Enum("DRAFT", "SUBMITTED", "INDUSTRY_REVIEWED", "REVIEWED", name="internship_work_log_status"), nullable=False, server_default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class InternshipWorkLogReview(Base):
    """Append-only review history authored by the placement's assigned faculty mentor."""
    __tablename__ = "internship_work_log_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_log_id: Mapped[str] = mapped_column(ForeignKey("internship_work_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(Enum("FACULTY", "INDUSTRY_MENTOR", name="internship_work_log_reviewer_role"), nullable=False)
    decision: Mapped[str] = mapped_column(Enum("ACKNOWLEDGED", "REVISION_REQUIRED", name="internship_work_log_review_decision"), nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
