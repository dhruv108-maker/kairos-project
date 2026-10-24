from datetime import datetime
from sqlalchemy import BigInteger, TIMESTAMP, ForeignKey, String, Enum, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class FacultyStudentMentorship(Base):
    __tablename__ = "faculty_student_mentorships"
    __table_args__ = (UniqueConstraint("institution_id", "faculty_profile_id", "student_profile_id", name="uq_mentorship_assignment"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False)
    faculty_profile_id: Mapped[str] = mapped_column(ForeignKey("faculty_profiles.id", ondelete="RESTRICT"), nullable=False)
    student_profile_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False)
    assigned_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(Enum("ACTIVE", "ENDED", name="mentorship_status"), nullable=False, server_default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
