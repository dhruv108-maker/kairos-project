from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RegistrationBase(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name cannot be blank")
        return value


class StudentRegistration(RegistrationBase):
    enrollment_number: str = Field(min_length=1, max_length=64)
    cohort_id: str = Field(min_length=1, max_length=36)

    @field_validator("enrollment_number")
    @classmethod
    def normalize_enrollment(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enrollment number cannot be blank")
        return value


class FacultyRegistration(RegistrationBase):
    employee_code: str = Field(min_length=1, max_length=64)
    department_id: str = Field(min_length=1, max_length=36)
    designation: str = Field(min_length=1, max_length=100)

    @field_validator("employee_code", "department_id", "designation")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=4096)


class ResendVerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Non-optional type rejects explicit null, while the default permits omission.
    full_name: str = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, max_length=32)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name cannot be blank")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AccountPublic(BaseModel):
    id: str
    email: str
    full_name: str
    phone_number: str | None
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None
    roles: list[str]


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    account: AccountPublic


class RegistrationResponse(BaseModel):
    account_id: str
    message: str
    verification_email_sent: bool
    activation_pending: bool = False


class MessageResponse(BaseModel):
    message: str


class StudentProfileResponse(BaseModel):
    account: AccountPublic
    student: dict[str, Any]


class FacultyProfileResponse(BaseModel):
    account: AccountPublic
    faculty: dict[str, Any]


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    new_password: str = Field(min_length=12, max_length=128)
