import asyncio
import pytest
from fastapi import HTTPException

from app.main import app
from app.modules.employers.hiringcafe_provider import HiringCafeProvider, HiringCafeSearchFilters, HiringCafeUnavailable
from app.modules.employers.hiringcafe_router import search_hiringcafe_jobs


def test_hiringcafe_provider_status_is_explicitly_disabled_without_fabricated_data():
    status = HiringCafeProvider().status()
    assert status["status"] == "disabled"
    assert status["available"] is False
    assert status["supports_search"] is False
    assert status["supports_job_details"] is False
    assert status["supports_saved_jobs"] is False
    assert status["last_refreshed_at"] is None
    assert "heavy automated use is unsupported" in status["message"]


def test_hiringcafe_search_filters_validate_documented_bounds_and_values():
    filters = HiringCafeSearchFilters(search="  graduate software engineer  ", location="  Ahmedabad  ",
        employment_types=["Internship", "Full Time"], seniority_levels=["Entry Level"], posted_within_days=7, limit=20)
    assert filters.search == "graduate software engineer"
    assert filters.location == "Ahmedabad"
    with pytest.raises(ValueError):
        HiringCafeSearchFilters(limit=26)
    with pytest.raises(ValueError):
        HiringCafeSearchFilters(workplace_types=["Remote", "Hybrid", "Onsite", "Remote"])


@pytest.mark.asyncio
async def test_hiringcafe_provider_fails_closed_for_search_and_details():
    provider = HiringCafeProvider()
    with pytest.raises(HiringCafeUnavailable) as search_error:
        await provider.search(HiringCafeSearchFilters(search="internship"))
    assert search_error.value.status_code == 503
    with pytest.raises(HiringCafeUnavailable) as details_error:
        await provider.get_details("any-id")
    assert details_error.value.status_code == 503


def test_hiringcafe_routes_are_registered_without_changing_native_routes():
    paths = app.openapi()["paths"]
    assert "/api/v1/jobs/providers" in paths
    assert "/api/v1/jobs/providers/hiringcafe/search" in paths
    assert "/api/v1/jobs/providers/hiringcafe/jobs/{job_id}" in paths
    assert "/api/v1/jobs" in paths
    assert "/api/v1/students/saved-jobs" in paths


def test_hiringcafe_search_route_returns_stable_unavailable_response(monkeypatch):
    async def disabled_search(filters):
        raise HiringCafeUnavailable()
    monkeypatch.setattr("app.modules.employers.hiringcafe_router._provider.search", disabled_search)
    with pytest.raises(HTTPException) as error:
        asyncio.run(search_hiringcafe_jobs(
            search="internship", location=None, workplace_types=[], radius_miles=50,
            employment_types=[], seniority_levels=[], min_salary=None, salary_frequency="Yearly",
            posted_salary_only=False, max_years_experience=None, posted_within_days=None,
            company_names=[], exclude_company_names=[], limit=20,
        ))
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "provider_unavailable"
