"""Source-aware, fail-closed external job-provider routes."""
from fastapi import APIRouter, HTTPException, Path, Query
from typing import Literal

from app.modules.employers.hiringcafe_provider import (
    HiringCafeProvider,
    HiringCafeSearchFilters,
    HiringCafeUnavailable,
)

router = APIRouter(tags=["external-job-providers"])
_provider = HiringCafeProvider()


@router.get("/jobs/providers")
async def list_job_providers():
    return {
        "items": [
            {
                "id": "kairos",
                "name": "Kairos",
                "status": "available",
                "available": True,
                "supports_search": True,
                "supports_job_details": True,
                "supports_saved_jobs": True,
                "supports_application_submission": True,
            },
            _provider.status(),
        ]
    }


@router.get("/jobs/providers/hiringcafe/search")
async def search_hiringcafe_jobs(
    search: str | None = Query(default=None, max_length=200),
    location: str | None = Query(default=None, max_length=120),
    workplace_types: list[Literal["Remote", "Hybrid", "Onsite"]] = Query(default=[]),
    radius_miles: int = Query(default=50, ge=1, le=250),
    employment_types: list[Literal["Full Time", "Part Time", "Contract", "Internship", "Temporary", "Seasonal", "Volunteer"]] = Query(default=[]),
    seniority_levels: list[Literal["No Prior Experience Required", "Entry Level", "Mid Level", "Senior Level"]] = Query(default=[]),
    min_salary: int | None = Query(default=None, ge=0, le=10_000_000),
    salary_frequency: Literal["Yearly", "Monthly", "Weekly", "Daily", "Hourly"] = "Yearly",
    posted_salary_only: bool = False,
    max_years_experience: int | None = Query(default=None, ge=0, le=60),
    posted_within_days: int | None = Query(default=None, ge=1, le=365),
    company_names: list[str] = Query(default=[]),
    exclude_company_names: list[str] = Query(default=[]),
    limit: int = Query(default=20, ge=1, le=25),
):
    filters = HiringCafeSearchFilters(
        search=search, location=location, workplace_types=workplace_types,
        radius_miles=radius_miles, employment_types=employment_types,
        seniority_levels=seniority_levels, min_salary=min_salary,
        salary_frequency=salary_frequency, posted_salary_only=posted_salary_only,
        max_years_experience=max_years_experience, posted_within_days=posted_within_days,
        company_names=company_names, exclude_company_names=exclude_company_names,
        limit=limit,
    )
    try:
        return await _provider.search(filters)
    except HiringCafeUnavailable as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message, "provider": "hiringcafe"},
            headers={"Cache-Control": "no-store"},
        ) from None


@router.get("/jobs/providers/hiringcafe/jobs/{job_id}")
async def get_hiringcafe_job_details(job_id: str = Path(..., min_length=1, max_length=200)):
    try:
        return await _provider.get_details(job_id)
    except HiringCafeUnavailable as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message, "provider": "hiringcafe"},
            headers={"Cache-Control": "no-store"},
        ) from None
