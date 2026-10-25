"""Regression tests for the industry-mentor authorization boundary.

These are isolated async unit tests: route handlers are invoked directly with a
mocked session, so no database engine or external service is contacted.
Run from backend/ with: pytest -q tests/test_industry_mentor_authorization.py
"""
import os

# The application builds its SQLAlchemy engine at import time. Outside CI,
# force harmless local test values rather than accidentally inheriting a developer
# or production database target. GitHub Actions supplies its disposable MySQL
# service settings and must retain those values for the existing integration suite.
_TEST_ENV = {
    "DB_HOST": "127.0.0.1",
    "DB_PORT": "3306",
    "DB_USER": "kairos_test",
    "DB_PASSWORD": "not-a-real-password",
    "DB_NAME": "kairos_test",
    "JWT_SECRET_KEY": "unit-test-secret-key-not-for-authentication",
}
if os.environ.get("CI", "").lower() == "true":
    for _key, _value in _TEST_ENV.items():
        os.environ.setdefault(_key, _value)
else:
    os.environ.update(_TEST_ENV)

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api import dependencies
from app.api.dependencies import get_current_account, get_db_session
from app.main import app
from app.modules.internships import router as internships_router
from app.modules.internships.schemas import WorkLogReviewCreate


@pytest.mark.asyncio
async def test_require_role_rejects_account_without_industry_mentor_role(monkeypatch):
    monkeypatch.setattr(dependencies, "account_roles", AsyncMock(return_value=["STUDENT"]))
    account = SimpleNamespace(id="student-account")

    with pytest.raises(HTTPException) as exc:
        await dependencies.require_role(AsyncMock(), account, "INDUSTRY_MENTOR")

    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient role"


@pytest.mark.asyncio
async def test_require_role_allows_industry_mentor(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "account_roles",
        AsyncMock(return_value=["INDUSTRY_MENTOR"]),
    )

    # A successful role check returns normally.
    await dependencies.require_role(
        AsyncMock(), SimpleNamespace(id="mentor-account"), "INDUSTRY_MENTOR"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler_name", "args"),
    [
        ("industry_mentor_placements", ()),
        ("industry_mentor_work_logs", ()),
        (
            "industry_mentor_review_work_log",
            (
                "protected-work-log",
                WorkLogReviewCreate(
                    decision="ACKNOWLEDGED",
                    feedback="Looks good",
                ),
            ),
        ),
    ],
)
async def test_non_mentor_is_rejected_before_resource_reads_or_mutations(
    monkeypatch, handler_name, args
):
    """Each protected route must invoke its role guard before touching data."""
    db = AsyncMock()
    account = SimpleNamespace(id="ordinary-student")
    guard = AsyncMock(side_effect=HTTPException(status_code=403, detail="Insufficient role"))
    monkeypatch.setattr(internships_router, "require_role", guard)
    handler = getattr(internships_router, handler_name)

    with pytest.raises(HTTPException) as exc:
        await handler(*args, account, db)

    assert exc.value.status_code == 403
    guard.assert_awaited_once_with(db, account, "INDUSTRY_MENTOR")
    db.execute.assert_not_awaited()
    db.get.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_unassigned_account_cannot_pass_industry_mentor_assignment_check():
    """The role alone is insufficient: the placement must be assigned to this account."""
    placement = SimpleNamespace(industry_mentor_account_id="mentor-A")
    db = AsyncMock()

    allowed = await internships_router._is_active_assigned_industry_mentor(
        db, placement, "mentor-B"
    )

    assert allowed is False
    db.get.assert_not_awaited()
    db.scalar.assert_not_awaited()



@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/v1/modules/internships/placements/mentor/me", None),
        ("GET", "/api/v1/modules/internships/work-logs/mentor/me", None),
        (
            "POST",
            "/api/v1/modules/internships/work-logs/protected-work-log/mentor-review",
            {"decision": "ACKNOWLEDGED", "feedback": "Looks good"},
        ),
    ],
)
async def test_http_routes_return_403_for_non_mentor_without_touching_resources(
    monkeypatch, method, path, payload
):
    """Exercise the mounted API surface, not just direct Python handler calls."""
    db = AsyncMock()
    account = SimpleNamespace(id="ordinary-student")
    monkeypatch.setattr(
        dependencies, "account_roles", AsyncMock(return_value=["STUDENT"])
    )

    async def override_account():
        return account

    async def override_db():
        yield db

    app.dependency_overrides[get_current_account] = override_account
    app.dependency_overrides[get_db_session] = override_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            if method == "GET":
                response = await client.get(path)
            else:
                response = await client.post(path, json=payload)

        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient role"
        db.execute.assert_not_awaited()
        db.get.assert_not_awaited()
        db.commit.assert_not_awaited()
        db.add.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_current_account, None)
        app.dependency_overrides.pop(get_db_session, None)
