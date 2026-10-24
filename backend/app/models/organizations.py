from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Date, TIMESTAMP, ForeignKey, String, Text, Enum, Boolean, UniqueConstraint, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    created_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class TeamMembership(Base):
    __tablename__ = "team_memberships"
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    role_in_team: Mapped[str] = mapped_column(String(50), nullable=False, server_default="MEMBER")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    joined_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class AssessmentCampaign(Base):
    __tablename__ = "assessment_campaigns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class FacultyAssessmentAssignment(Base):
    __tablename__ = "faculty_assessment_assignments"
    __table_args__ = (UniqueConstraint("campaign_id", "faculty_id", name="uq_campaign_faculty_assignment"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("assessment_campaigns.id", ondelete="CASCADE"), nullable=False)
    faculty_id: Mapped[str] = mapped_column(ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False)
    assigned_reason: Mapped[str] = mapped_column(String(100), nullable=False, server_default="RANDOM_SELECTION")
    status: Mapped[str] = mapped_column(Enum("PENDING", "IN_PROGRESS", "SUBMITTED", "EXPIRED", name="faculty_assessment_status"), nullable=False, server_default="PENDING")
    assigned_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    feedback_comments: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
