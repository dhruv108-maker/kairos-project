"""Pydantic v2 request/response contracts for the internship domain."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class ProviderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_name: str = Field(min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    industry_sector: str | None = Field(default=None, max_length=100)
    contact_person_name: str | None = Field(default=None, max_length=150)
    contact_email: str | None = Field(default=None, max_length=255)
    @field_validator("company_name")
    @classmethod
    def clean_company_name(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("Company name cannot be blank")
        return value

class OpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=150)
    stipend_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    application_deadline: date
    @field_validator("title", "description", "location")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("This field cannot be blank")
        return value

class ApplicationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        value = value.strip().upper()
        # The supplied DDL enum doesn't currently contain ACCEPTED.
        if value not in {"SHORTLISTED", "OFFERED", "REJECTED"}: raise ValueError("status must be SHORTLISTED, OFFERED, or REJECTED")
        return value

class PlacementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date
    end_date: date
    faculty_supervisor_id: str | None = Field(default=None, max_length=36)
    @model_validator(mode="after")
    def validate_range(self):
        if self.end_date < self.start_date: raise ValueError("end_date must be on or after start_date")
        return self
