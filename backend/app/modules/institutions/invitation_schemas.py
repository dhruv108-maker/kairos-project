from pydantic import BaseModel, Field, field_validator
import re


class InstitutionInvitationCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: str = Field(pattern=r"^(FACULTY|MEMBER)$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value):
            raise ValueError("Enter a valid email address")
        return value


class InstitutionInvitationAccept(BaseModel):
    token: str = Field(min_length=30, max_length=256)
