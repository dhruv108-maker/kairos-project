from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.dependencies import get_current_account
from app.core.database import get_db_session
from app.main import app
from app.models import (
    AcademicYear, Account, AccountRole, Base, Cohort, Department, Programme,
    Role, School, StudentAcademicRecord, StudentProfile,
)


@pytest_asyncio.fixture
async def portfolio_api():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        school = School(id="school-1", code="SCH", name="Example School")
        session.add(school)
        await session.commit()
        department = Department(id="dept-1", school_id=school.id, code="CSE", name="Computing")
        session.add(department)
        await session.commit()
        programme = Programme(id="programme-1", department_id=department.id, code="BSC",
                              name="Computer Science", degree_level="undergraduate", duration_years=3)
        year = AcademicYear(id="year-1", year_label="2026-27", start_date=date(2026, 4, 1),
                            end_date=date(2027, 3, 31), is_current=True)
        session.add_all([programme, year])
        await session.commit()
        cohort = Cohort(id="cohort-1", programme_id=programme.id, academic_year_id=year.id,
                        name="Batch 2026", graduation_year=2029)
        role = Role(id="role-student", name="STUDENT", description="Student")
        first = Account(id="account-1", email="one@example.test", password_hash="not-used",
                        full_name="Student One", phone_number=None, is_active=True, is_verified=True)
        second = Account(id="account-2", email="two@example.test", password_hash="not-used",
                         full_name="Student Two", phone_number=None, is_active=True, is_verified=True)
        session.add_all([cohort, role, first, second])
        await session.commit()
        first_profile = StudentProfile(id=1, student_id=1001, account_id=first.id, enrollment_number="ENR-1",
                                       cohort_id=cohort.id, current_semester=1)
        second_profile = StudentProfile(id=2, student_id=1002, account_id=second.id, enrollment_number="ENR-2",
                                        cohort_id=cohort.id, current_semester=1)
        session.add_all([first_profile, second_profile,
                         AccountRole(account_id=first.id, role_id=role.id),
                         AccountRole(account_id=second.id, role_id=role.id)])
        await session.commit()

    current_account = {"value": first}

    async def override_db():
        async with session_factory() as session:
            yield session

    async def override_account():
        return current_account["value"]

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_account] = override_account
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    context = {"client": client, "account": current_account, "first": first, "second": second,
               "first_profile": first_profile, "second_profile": second_profile,
               "session_factory": session_factory}
    try:
        yield context
    finally:
        await client.aclose()
        app.dependency_overrides.pop(get_current_account, None)
        app.dependency_overrides.pop(get_db_session, None)
        await engine.dispose()


@pytest.mark.asyncio
async def test_portfolio_crud_is_scoped_to_authenticated_student(portfolio_api):
    client = portfolio_api["client"]
    created = await client.post("/api/v1/students/me/skills",
                                json={"title": "Python", "proficiency": "advanced"})
    assert created.status_code == 201
    record_id = created.json()["id"]
    portfolio_api["account"]["value"] = portfolio_api["second"]
    assert (await client.get("/api/v1/students/me/skills")).json()["items"] == []
    assert (await client.get(f"/api/v1/students/me/skills/{record_id}")).status_code == 404
    assert (await client.patch(f"/api/v1/students/me/skills/{record_id}",
                               json={"title": "Hijacked"})).status_code == 404
    assert (await client.delete(f"/api/v1/students/me/skills/{record_id}")).status_code == 404
    portfolio_api["account"]["value"] = portfolio_api["first"]
    assert (await client.get(f"/api/v1/students/me/skills/{record_id}")).status_code == 200
    assert (await client.delete(f"/api/v1/students/me/skills/{record_id}")).status_code == 204


@pytest.mark.asyncio
async def test_portfolio_rejects_privileged_fields_unsafe_urls_and_oversized_text(portfolio_api):
    client = portfolio_api["client"]
    spoofed = await client.post("/api/v1/students/me/skills",
                                json={"title": "Python", "student_profile_id": "student-2",
                                      "is_verified": True})
    assert spoofed.status_code == 422
    unsafe_url = await client.post("/api/v1/students/me/projects",
                                   json={"title": "Demo", "url": "javascript:alert(1)"})
    assert unsafe_url.status_code == 422
    oversized = await client.post("/api/v1/students/me/projects",
                                  json={"title": "Demo", "description": "x" * 10001})
    assert oversized.status_code == 422


@pytest.mark.asyncio
async def test_academic_verification_fields_are_not_student_writable(portfolio_api):
    client = portfolio_api["client"]
    created = await client.post("/api/v1/students/me/academic-records", json={
        "institution_name": "Example Institute", "qualification": "BSc",
        "grade_value": 8.2, "grade_max": 10,
    })
    assert created.status_code == 201
    record_id = created.json()["id"]
    assert created.json()["is_verified"] is False
    forbidden = await client.patch(f"/api/v1/students/me/academic-records/{record_id}",
                                   json={"is_verified": True})
    assert forbidden.status_code == 422
    async with portfolio_api["session_factory"]() as session:
        record = await session.get(StudentAcademicRecord, record_id)
        assert record is not None and record.is_verified is False


@pytest.mark.asyncio
async def test_cv_and_timeline_use_persisted_portfolio_data(portfolio_api):
    client = portfolio_api["client"]
    created = await client.post("/api/v1/students/me/projects", json={
        "title": "Kairos", "description": "Portfolio API integration test",
        "start_date": "2026-01-10",
    })
    assert created.status_code == 201
    cv = await client.get("/api/v1/students/me/cv")
    assert cv.status_code == 200
    assert any(item["title"] == "Kairos" for item in cv.json()["projects"])
    timeline = await client.get("/api/v1/students/me/timeline")
    assert timeline.status_code == 200
    assert any(item["title"] == "Kairos" and item["kind"] == "project"
               for item in timeline.json()["items"])


@pytest.mark.asyncio
async def test_student_endpoints_require_authentication(portfolio_api):
    app.dependency_overrides.pop(get_current_account, None)
    response = await portfolio_api["client"].get("/api/v1/students/me")
    assert response.status_code == 401
