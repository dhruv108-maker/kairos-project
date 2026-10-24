from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class EmployerRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_name: str = Field(min_length=2, max_length=255)
    display_name: str = Field(min_length=2, max_length=255)
    organization_type: str = "COMPANY"
    industry: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=10000)
    website_url: HttpUrl | None = None
    business_email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=30)
    headquarters_address: str | None = Field(default=None, max_length=500)
    company_size: str | None = Field(default=None, max_length=30)
    founded_year: int | None = Field(default=None, ge=1800, le=2100)
    registration_identifier: str | None = Field(default=None, max_length=120)
    careers_url: HttpUrl | None = None

    @field_validator("legal_name", "display_name")
    @classmethod
    def trim_names(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least two non-space characters")
        return value

    @field_validator("organization_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"COMPANY", "STARTUP", "NONPROFIT", "AGENCY", "OTHER"}:
            raise ValueError("Unsupported organization type")
        return value

    @field_validator("business_email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else None


class EmployerProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = Field(default=None, min_length=2, max_length=255)
    industry: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=10000)
    website_url: HttpUrl | None = None
    business_email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=30)
    headquarters_address: str | None = Field(default=None, max_length=500)
    company_size: str | None = Field(default=None, max_length=30)
    founded_year: int | None = Field(default=None, ge=1800, le=2100)
    careers_url: HttpUrl | None = None


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=2, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    description: str = Field(min_length=20, max_length=30000)
    opportunity_type: str = "INTERNSHIP"
    employment_type: str = "INTERNSHIP"
    work_mode: str = "ONSITE"
    location: str = Field(min_length=2, max_length=150)
    department: str | None = Field(default=None, max_length=120)
    experience_min_years: Decimal | None = Field(default=None, ge=0, le=60)
    experience_max_years: Decimal | None = Field(default=None, ge=0, le=60)
    compensation_min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    compensation_max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    compensation_currency: str = Field(default="INR", min_length=3, max_length=3)
    compensation_period: str = "YEAR"
    compensation_visible: bool = True
    application_deadline: date
    starts_on: date | None = None
    ends_on: date | None = None
    openings: int = Field(default=1, ge=1, le=100000)
    required_skills: list[str] = Field(default_factory=list, max_length=100)
    preferred_skills: list[str] = Field(default_factory=list, max_length=100)
    education_requirements: str | None = Field(default=None, max_length=2000)
    public_application_url: HttpUrl | None = None

    @field_validator("opportunity_type")
    @classmethod
    def valid_opportunity_type(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"JOB", "INTERNSHIP"}:
            raise ValueError("opportunity_type must be JOB or INTERNSHIP")
        return value

    @field_validator("employment_type")
    @classmethod
    def valid_employment_type(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"FULL_TIME", "PART_TIME", "INTERNSHIP", "CONTRACT", "TEMPORARY"}:
            raise ValueError("Unsupported employment_type")
        return value

    @field_validator("work_mode")
    @classmethod
    def valid_work_mode(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"ONSITE", "HYBRID", "REMOTE"}:
            raise ValueError("work_mode must be ONSITE, HYBRID, or REMOTE")
        return value

    @field_validator("compensation_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("compensation_currency must be a three-letter currency code")
        return value

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.compensation_min is not None and self.compensation_max is not None and self.compensation_max < self.compensation_min:
            raise ValueError("compensation_max must be greater than or equal to compensation_min")
        if self.experience_min_years is not None and self.experience_max_years is not None and self.experience_max_years < self.experience_min_years:
            raise ValueError("experience_max_years must be greater than or equal to experience_min_years")
        if self.ends_on and self.starts_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        if self.opportunity_type == "INTERNSHIP" and self.employment_type != "INTERNSHIP":
            raise ValueError("Internship opportunities must use employment_type=INTERNSHIP")
        return self


class JobPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=2, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, min_length=20, max_length=30000)
    opportunity_type: str | None = None
    employment_type: str | None = None
    work_mode: str | None = None
    location: str | None = Field(default=None, min_length=2, max_length=150)
    department: str | None = Field(default=None, max_length=120)
    experience_min_years: Decimal | None = Field(default=None, ge=0, le=60)
    experience_max_years: Decimal | None = Field(default=None, ge=0, le=60)
    compensation_min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    compensation_max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    compensation_currency: str | None = Field(default=None, min_length=3, max_length=3)
    compensation_period: str | None = None
    compensation_visible: bool | None = None
    application_deadline: date | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    openings: int | None = Field(default=None, ge=1, le=100000)
    required_skills: list[str] | None = Field(default=None, max_length=100)
    preferred_skills: list[str] | None = Field(default=None, max_length=100)
    education_requirements: str | None = Field(default=None, max_length=2000)
    public_application_url: HttpUrl | None = None

    @field_validator("opportunity_type")
    @classmethod
    def valid_opportunity_type(cls, value: str | None) -> str | None:
        if value is None: return value
        value = value.strip().upper()
        if value not in {"JOB", "INTERNSHIP"}: raise ValueError("opportunity_type must be JOB or INTERNSHIP")
        return value

    @field_validator("employment_type")
    @classmethod
    def valid_employment_type(cls, value: str | None) -> str | None:
        if value is None: return value
        value = value.strip().upper()
        if value not in {"FULL_TIME", "PART_TIME", "INTERNSHIP", "CONTRACT", "TEMPORARY"}: raise ValueError("Unsupported employment_type")
        return value

    @field_validator("work_mode")
    @classmethod
    def valid_work_mode(cls, value: str | None) -> str | None:
        if value is None: return value
        value = value.strip().upper()
        if value not in {"ONSITE", "HYBRID", "REMOTE"}: raise ValueError("work_mode must be ONSITE, HYBRID, or REMOTE")
        return value

    @field_validator("compensation_currency")
    @classmethod
    def normalize_patch_currency(cls, value: str | None) -> str | None:
        if value is None: return value
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha(): raise ValueError("compensation_currency must be a three-letter currency code")
        return value


class InterviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=480)
    interview_type: str = "VIDEO"
    meeting_url: HttpUrl | None = None
    location: str | None = Field(default=None, max_length=500)
    interviewer_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("interview_type")
    @classmethod
    def valid_interview_type(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"VIDEO", "PHONE", "ONSITE", "ASSESSMENT"}:
            raise ValueError("Unsupported interview type")
        return value

    @model_validator(mode="after")
    def validate_location(self):
        if self.scheduled_at.tzinfo is None or self.scheduled_at.utcoffset() is None:
            raise ValueError("scheduled_at must include a timezone offset")
        if self.interview_type == "VIDEO" and self.meeting_url is None:
            raise ValueError("Video interviews require a meeting_url")
        if self.interview_type == "ONSITE" and not self.location:
            raise ValueError("Onsite interviews require a location")
        return self


class InterviewStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"SCHEDULED", "COMPLETED", "CANCELLED", "NO_SHOW"}:
            raise ValueError("Unsupported interview status")
        return value


class OfferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    compensation_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    compensation_currency: str = Field(default="INR", min_length=3, max_length=3)
    compensation_period: str = "YEAR"
    start_date: date | None = None
    expires_at: datetime | None = None
    terms: str | None = Field(default=None, max_length=20000)

    @field_validator("compensation_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha(): raise ValueError("compensation_currency must be a three-letter currency code")
        return value

    @field_validator("expires_at")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("expires_at must include a timezone offset")
        return value


class OfferStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"ISSUED", "ACCEPTED", "DECLINED", "WITHDRAWN"}:
            raise ValueError("Unsupported offer status")
        return value


class EmployerInviteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=5, max_length=255)
    role: str = "RECRUITER"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"ADMIN", "RECRUITER", "VIEWER"}:
            raise ValueError("role must be ADMIN, RECRUITER, or VIEWER")
        return value


class EmployerInviteAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=200)


class EmployerRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"ADMIN", "RECRUITER", "VIEWER"}:
            raise ValueError("role must be ADMIN, RECRUITER, or VIEWER")
        return value


class RecruitmentStageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: str
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("stage")
    @classmethod
    def valid_stage(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"SUBMITTED", "UNDER_REVIEW", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED", "REJECTED", "WITHDRAWN"}:
            raise ValueError("Unsupported recruitment stage")
        return value


class RecruitmentNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def nonblank_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Note cannot be blank")
        return value


class EmployerStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(ACTIVE|SUSPENDED|REJECTED|PENDING_APPROVAL)$")
    notes: str | None = Field(default=None, max_length=2000)
