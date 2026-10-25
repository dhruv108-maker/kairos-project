from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Date, TIMESTAMP, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint, Numeric, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
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
    # The deployed assessment schema uses unsigned auto-increment BIGINT identifiers.
    id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True, autoincrement=True,
    )
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class FacultyAssessmentAssignment(Base):
    """ORM mapping for the deployed assessment_assignments table."""
    __tablename__ = "assessment_assignments"
    __table_args__ = (
        UniqueConstraint("campaign_id", "faculty_id", name="uq_campaign_faculty"),
    )
    id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True).with_variant(Integer, "sqlite"),
        primary_key=True, autoincrement=True,
    )
    campaign_id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True), ForeignKey("assessment_campaigns.id"), nullable=False
    )
    faculty_id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True), ForeignKey("faculty.id"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    assignment_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="assigned")
    selection_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
