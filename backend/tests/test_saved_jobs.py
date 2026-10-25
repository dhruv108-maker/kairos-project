import pytest
from fastapi import HTTPException

from app.main import app
from app.modules.employers.saved_jobs_router import _require_student


def test_saved_job_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "/api/v1/students/saved-jobs" in paths
    assert "/api/v1/students/saved-jobs/{opportunity_id}" in paths
    search_parameters = {item["name"] for item in paths["/api/v1/jobs"]["get"]["parameters"]}
    assert {"employment_type", "sort_by", "posted_within_days"}.issubset(search_parameters)


def test_saved_job_routes_require_authenticated_student():
    paths = app.openapi()["paths"]
    get_security = paths["/api/v1/students/saved-jobs"]["get"].get("security")
    post_security = paths["/api/v1/students/saved-jobs/{opportunity_id}"]["post"].get("security")
    assert get_security and post_security


@pytest.mark.asyncio
async def test_non_student_roles_are_denied(monkeypatch):
    class FakeIdentity:
        def __init__(self, db):
            pass
        async def roles_for(self, account_id):
            return ["FACULTY"]

    monkeypatch.setattr("app.modules.employers.saved_jobs_router.IdentityService", FakeIdentity)
    with pytest.raises(HTTPException) as exc:
        await _require_student(None, "faculty-account")
    assert exc.value.status_code == 403
