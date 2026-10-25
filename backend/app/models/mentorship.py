from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FacultyStudentMentorship(Base):
    """ORM mapping for the deployed MySQL faculty_mentorships table."""

    __tablename__ = "faculty_mentorships"

    id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    institution_id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    faculty_id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True),
        ForeignKey("faculty.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
    )
    academic_year_id: Mapped[int | None] = mapped_column(
        MYSQL_BIGINT(unsigned=True),
        ForeignKey("academic_years.id", ondelete="RESTRICT"),
        nullable=True,
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    assigned_by_account_id: Mapped[int | None] = mapped_column(
        MYSQL_BIGINT(unsigned=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now()
    )
