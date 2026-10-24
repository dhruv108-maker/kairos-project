"""Institution-scoped campus recruitment drives and their relational targeting."""
from datetime import date, datetime
from sqlalchemy import Date, ForeignKey, Integer, String, Text, TIMESTAMP, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class RecruitmentDrive(Base):
    __tablename__ = "recruitment_drives"
    __table_args__ = (
        Index("ix_recruitment_drives_institution_status", "institution_id", "status"),
        Index("ix_recruitment_drives_application_window", "application_opens_at", "application_closes_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False)
    academic_year_id: Mapped[str | None] = mapped_column(ForeignKey("academic_years.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    application_opens_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    application_closes_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="DRAFT")
    created_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class RecruitmentDriveProgrammeTarget(Base):
    __tablename__ = "recruitment_drive_programme_targets"
    __table_args__ = (UniqueConstraint("drive_id", "programme_id", name="uq_drive_programme_target"),)
    drive_id: Mapped[str] = mapped_column(ForeignKey("recruitment_drives.id", ondelete="CASCADE"), primary_key=True)
    programme_id: Mapped[str] = mapped_column(ForeignKey("programmes.id", ondelete="RESTRICT"), primary_key=True)


class RecruitmentDriveCohortTarget(Base):
    __tablename__ = "recruitment_drive_cohort_targets"
    __table_args__ = (UniqueConstraint("drive_id", "cohort_id", name="uq_drive_cohort_target"),)
    drive_id: Mapped[str] = mapped_column(ForeignKey("recruitment_drives.id", ondelete="CASCADE"), primary_key=True)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohorts.id", ondelete="RESTRICT"), primary_key=True)


class RecruitmentDriveGraduationYearTarget(Base):
    __tablename__ = "recruitment_drive_graduation_year_targets"
    __table_args__ = (UniqueConstraint("drive_id", "graduation_year", name="uq_drive_graduation_year_target"),)
    drive_id: Mapped[str] = mapped_column(ForeignKey("recruitment_drives.id", ondelete="CASCADE"), primary_key=True)
    graduation_year: Mapped[int] = mapped_column(Integer, primary_key=True)


class RecruitmentDriveParticipation(Base):
    __tablename__ = "recruitment_drive_participations"
    __table_args__ = (
        UniqueConstraint("drive_id", "organization_id", name="uq_drive_employer_participation"),
        Index("ix_drive_participation_org_status", "organization_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    drive_id: Mapped[str] = mapped_column(ForeignKey("recruitment_drives.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey("employer_organizations.id", ondelete="RESTRICT"), nullable=False)
    invited_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="INVITED")
    responded_by_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    invited_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class RecruitmentDriveOpportunity(Base):
    __tablename__ = "recruitment_drive_opportunities"
    __table_args__ = (
        UniqueConstraint("drive_id", "opportunity_id", name="uq_drive_opportunity"),
        Index("ix_drive_opportunity_opportunity", "opportunity_id"),
    )
    drive_id: Mapped[str] = mapped_column(ForeignKey("recruitment_drives.id", ondelete="CASCADE"), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("internship_opportunities.id", ondelete="RESTRICT"), primary_key=True)
    added_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
