from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, Date, TIMESTAMP, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())


class School(TimestampMixin, Base):
    __tablename__ = "schools"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    departments: Mapped[list["Department"]] = relationship(back_populates="school")


class Department(TimestampMixin, Base):
    __tablename__ = "departments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    school: Mapped[School] = relationship(back_populates="departments")
    programmes: Mapped[list["Programme"]] = relationship(back_populates="department")


class Programme(TimestampMixin, Base):
    __tablename__ = "programmes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # The deployed catalogue uses status for public eligibility; degree metadata varies
    # across legacy schemas and is not required to render the registration selector.
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    degree_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_years: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="4")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    department: Mapped[Department] = relationship(back_populates="programmes")
    cohorts: Mapped[list["Cohort"]] = relationship(back_populates="programme")


class AcademicYear(Base):
    __tablename__ = "academic_years"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    year_label: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    cohorts: Mapped[list["Cohort"]] = relationship(back_populates="academic_year")


class Cohort(Base):
    __tablename__ = "cohorts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    programme_id: Mapped[str] = mapped_column(ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False)
    academic_year_id: Mapped[str] = mapped_column(ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    programme: Mapped[Programme] = relationship(back_populates="cohorts")
    academic_year: Mapped[AcademicYear] = relationship(back_populates="cohorts")
    students: Mapped[list["StudentProfile"]] = relationship(back_populates="cohort")


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    verification_token: Mapped[str | None] = mapped_column(String(128))
    reset_token: Mapped[str | None] = mapped_column(String(128))
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    roles: Mapped[list["AccountRole"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    student_profile: Mapped["StudentProfile | None"] = relationship(back_populates="account", uselist=False)
    faculty_profile: Mapped["FacultyProfile | None"] = relationship(back_populates="account", uselist=False)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    accounts: Mapped[list["AccountRole"]] = relationship(back_populates="role", cascade="all, delete-orphan")


class AccountRole(Base):
    __tablename__ = "account_roles"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    account: Mapped[Account] = relationship(back_populates="roles")
    role: Mapped[Role] = relationship(back_populates="accounts")


class Student(Base):
    """Canonical numeric student row from the deployed MySQL schema."""
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(MYSQL_BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True), ForeignKey("accounts.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    student_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False)
    enrollment_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    profile_photo_url: Mapped[str | None] = mapped_column(String(500))
    bio: Mapped[str | None] = mapped_column(Text)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    profile_visibility: Mapped[str] = mapped_column(String(20), nullable=False, server_default="private")
    is_profile_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    # Department affiliation is established at signup; cohort assignment can happen later.
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, index=True)
    programme_id: Mapped[str | None] = mapped_column(ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=True, index=True)
    cohort_id: Mapped[str | None] = mapped_column(ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=True)
    current_semester: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    cgpa: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    account: Mapped[Account] = relationship(back_populates="student_profile")
    cohort: Mapped["Cohort | None"] = relationship(back_populates="students")
    department: Mapped["Department | None"] = relationship()


class FacultyProfile(Base):
    """Faculty row mapped to the deployed MySQL `faculty` table.

    The live identity schema uses BIGINT UNSIGNED auto-increment identifiers;
    it does not contain the legacy `faculty_profiles` UUID table.
    """
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(MYSQL_BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        MYSQL_BIGINT(unsigned=True), ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    employee_number: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    employee_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    employment_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    department_id: Mapped[int | None] = mapped_column(MYSQL_BIGINT(unsigned=True), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    account: Mapped[Account] = relationship(back_populates="faculty_profile")
