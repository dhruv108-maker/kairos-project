"""HiringCafe provider boundary.

The official ChatGPT MCP service is a conversational integration and explicitly does
not support heavy automated use. Kairos intentionally does not call it from a
multi-user SaaS backend. Replace this adapter only after an approved production
API/feed contract and permission are obtained.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

HIRINGCAFE_DOCUMENTATION_URL = "https://hiringcafe.com/documentation/hiringcafe-chatgpt-app"
HIRINGCAFE_WEBSITE_URL = "https://hiringcafe.com/"
HIRINGCAFE_BLOCK_REASON = (
    "Live HiringCafe search is disabled until HiringCafe provides permission and a "
    "production-suitable API or feed for multi-user SaaS use. Its documented ChatGPT "
    "MCP integration says heavy automated use is unsupported."
)


class HiringCafeUnavailable(Exception):
    status_code = 503
    code = "provider_unavailable"

    def __init__(self, message: str = HIRINGCAFE_BLOCK_REASON):
        self.message = message
        super().__init__(message)


class HiringCafeSearchFilters(BaseModel):
    """Validated subset of filters documented by HiringCafe's ChatGPT MCP tool."""

    model_config = ConfigDict(extra="forbid")

    search: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=120)
    workplace_types: list[Literal["Remote", "Hybrid", "Onsite"]] = Field(default_factory=list, max_length=3)
    radius_miles: int = Field(default=50, ge=1, le=250)
    employment_types: list[Literal["Full Time", "Part Time", "Contract", "Internship", "Temporary", "Seasonal", "Volunteer"]] = Field(default_factory=list, max_length=7)
    seniority_levels: list[Literal["No Prior Experience Required", "Entry Level", "Mid Level", "Senior Level"]] = Field(default_factory=list, max_length=4)
    min_salary: int | None = Field(default=None, ge=0, le=10_000_000)
    salary_frequency: Literal["Yearly", "Monthly", "Weekly", "Daily", "Hourly"] = "Yearly"
    posted_salary_only: bool = False
    max_years_experience: int | None = Field(default=None, ge=0, le=60)
    posted_within_days: int | None = Field(default=None, ge=1, le=365)
    company_names: list[str] = Field(default_factory=list, max_length=20)
    exclude_company_names: list[str] = Field(default_factory=list, max_length=20)
    limit: int = Field(default=20, ge=1, le=25)

    @field_validator("search", "location")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("company_names", "exclude_company_names")
    @classmethod
    def normalize_company_names(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            name = value.strip()
            if not name or len(name) > 120:
                raise ValueError("Company names must contain 1–120 characters")
            if name.casefold() not in {item.casefold() for item in normalized}:
                normalized.append(name)
        return normalized


class HiringCafeProvider:
    """Integration boundary; intentionally fail-closed until an approved API exists."""

    def status(self) -> dict:
        return {
            "id": "hiringcafe",
            "name": "HiringCafe",
            "status": "disabled",
            "available": False,
            "reason_code": "production_api_permission_required",
            "message": HIRINGCAFE_BLOCK_REASON,
            "documentation_url": HIRINGCAFE_DOCUMENTATION_URL,
            "website_url": HIRINGCAFE_WEBSITE_URL,
            "supports_search": False,
            "supports_job_details": False,
            "supports_saved_jobs": False,
            "supports_application_submission": False,
            "last_refreshed_at": None,
        }

    async def search(self, filters: HiringCafeSearchFilters) -> dict:
        del filters
        raise HiringCafeUnavailable()

    async def get_details(self, job_id: str) -> dict:
        del job_id
        raise HiringCafeUnavailable()
