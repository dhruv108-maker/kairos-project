"""Validated request schemas for institution and academic administration."""
import re
from datetime import date
from pydantic import BaseModel, Field, HttpUrl, field_validator


class InstitutionDomainCreate(BaseModel):
    domain: str = Field(min_length=3, max_length=253)

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, value: str) -> str:
        domain = value.strip().lower().rstrip(".")
        if not re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}", domain):
            raise ValueError("Enter a valid fully-qualified email domain")
        return domain


class InstitutionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=100)
    contact_email: str | None = Field(default=None, max_length=255)
    website_url: HttpUrl | None = None


class InstitutionRegistrationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=100)
    institution_type: str = Field(default="COLLEGE", pattern=r"^(UNIVERSITY|COLLEGE|TRAINING_INSTITUTE|SCHOOL|OTHER)$")
    contact_email: str | None = Field(default=None, max_length=255)
    website_url: HttpUrl | None = None
    registration_number: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    address: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=30)


class InstitutionStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(ACTIVE|SUSPENDED|PENDING|REJECTED)$")


class MembershipUpsert(BaseModel):
    account_id: str
    role: str = Field(pattern=r"^(INSTITUTION_ADMIN|FACULTY|MEMBER)$")


class SchoolCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=2, max_length=255)


class DepartmentCreate(SchoolCreate):
    school_id: str


class ProgrammeCreate(BaseModel):
    department_id: str
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=2, max_length=255)
    degree_level: str = Field(min_length=1, max_length=50)
    duration_years: int = Field(ge=1, le=12)


class AcademicYearCreate(BaseModel):
    year_label: str = Field(min_length=1, max_length=32)
    start_date: date
    end_date: date
    is_current: bool = False


class CohortCreate(BaseModel):
    programme_id: str
    academic_year_id: str
    name: str = Field(min_length=1, max_length=100)
    graduation_year: int = Field(ge=2000, le=2200)


class SchoolUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None


class ProgrammeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    degree_level: str | None = Field(default=None, min_length=1, max_length=50)
    duration_years: int | None = Field(default=None, ge=1, le=12)
    is_active: bool | None = None


class AcademicYearUpdate(BaseModel):
    year_label: str | None = Field(default=None, min_length=1, max_length=32)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None


class CohortUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    graduation_year: int | None = Field(default=None, ge=2000, le=2200)
    programme_id: str | None = None
    academic_year_id: str | None = None
