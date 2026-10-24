from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.auth as auth_module
from app.api.dependencies import get_db_session
from app.main import app
from app.models import Account, Base, Institution, InstitutionDomain
from app.models.academic import AcademicYear, Cohort, Department, Programme, School


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        admin = Account(id="domain-admin", email="admin@example.test", password_hash="x", full_name="Admin", is_active=True, is_verified=True)
        institution = Institution(id="institution-1", name="Sagiros University", slug="sagiros-university", status="ACTIVE", created_by_account_id=admin.id)
        other_institution = Institution(id="institution-2", name="Other University", slug="other-university", status="ACTIVE", created_by_account_id=admin.id)
        session.add_all([admin, institution, other_institution])
        await session.flush()
        session.add_all([
            InstitutionDomain(id="domain-1", institution_id=institution.id, normalized_domain="sagiros.edu.test", is_verified=True),
            School(id="school-1", institution_id="institution-1", code="SAG", name="Sagiros"),
            Department(
                id="department-1", school_id="school-1", code="CSE",
                name="Computer Science", is_active=True,
            ),
            Programme(
                id="programme-1", department_id="department-1", code="BTECH-CSE",
                name="B.Tech Computer Science", degree_level="Undergraduate",
                duration_years=4, is_active=True,
            ),
            AcademicYear(
                id="year-1", year_label="2026-2027", start_date=date(2026, 6, 1),
                end_date=date(2027, 5, 31), is_current=True,
            ),
            Cohort(
                id="cohort-1", programme_id="programme-1", academic_year_id="year-1",
                name="B.Tech CSE 2026", graduation_year=2030,
            ),
        ])
        await session.commit()

    async def override_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    sent_tokens = {}

    async def fake_send(email: str, token: str) -> None:
        sent_tokens[email] = token

    monkeypatch.setattr(auth_module, "send_verification_email", fake_send)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client, sent_tokens
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_student_signup_verification_login_and_profile(client):
    http, sent_tokens = client
    signup = await http.post("/api/v1/auth/register/student", json={
        "email": "  STUDENT@example.com ",
        "password": "a secure student password 42",
        "full_name": "Student One",
        "enrollment_number": "ENR-001",
        "cohort_id": "cohort-1",
    })
    assert signup.status_code == 201
    assert signup.json()["verification_email_sent"] is True
    assert "student@example.com" in sent_tokens

    before_verify = await http.post("/api/v1/auth/login", json={
        "email": "student@example.com",
        "password": "a secure student password 42",
    })
    assert before_verify.status_code == 401

    verified = await http.post("/api/v1/auth/verify-email", json={
        "token": sent_tokens["student@example.com"],
    })
    assert verified.status_code == 200

    login = await http.post("/api/v1/auth/login", json={
        "email": "student@example.com",
        "password": "a secure student password 42",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = await http.get("/api/v1/students/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["student"]["enrollment_number"] == "ENR-001"
    assert profile.json()["account"]["roles"] == ["STUDENT"]

    update = await http.patch(
        "/api/v1/students/me",
        headers=headers,
        json={"full_name": "Updated Student"},
    )
    assert update.status_code == 200
    assert update.json()["account"]["full_name"] == "Updated Student"

    escalation = await http.patch(
        "/api/v1/students/me",
        headers=headers,
        json={"is_active": True, "roles": ["SYSTEM_ADMIN"]},
    )
    assert escalation.status_code == 422


@pytest.mark.asyncio
async def test_institution_lookup_and_student_registration_preserve_academic_relationships(client):
    http, sent_tokens = client
    lookup = await http.get("/api/v1/institutions/resolve", params={"email_domain": "SAGIROS.EDU.TEST."})
    assert lookup.status_code == 200
    assert lookup.json() == {"status": "matched", "institution": {"id": "institution-1", "name": "Sagiros University"}}
    options = await http.get("/api/v1/institutions/public/institution-1/academic-options")
    assert options.status_code == 200
    assert [item["id"] for item in options.json()["departments"]] == ["department-1"]
    assert [item["id"] for item in options.json()["cohorts"]] == ["cohort-1"]

    signup = await http.post("/api/v1/auth/register/student", json={
        "email": "student@sagiros.edu.test", "password": "institution-aware password 42",
        "full_name": "Institution Student", "institution_id": "institution-1",
        "enrollment_number": "SAG-ENR-01", "cohort_id": "cohort-1",
    })
    assert signup.status_code == 201, signup.text
    verified = await http.post("/api/v1/auth/verify-email", json={"token": sent_tokens["student@sagiros.edu.test"]})
    assert verified.status_code == 200
    login = await http.post("/api/v1/auth/login", json={"email": "student@sagiros.edu.test", "password": "institution-aware password 42"})
    assert login.status_code == 200
    profile = await http.get("/api/v1/students/me", headers={"Authorization": "Bearer " + login.json()["access_token"]})
    assert profile.status_code == 200
    assert profile.json()["student"]["cohort_id"] == "cohort-1"
    assert profile.json()["account"]["full_name"] == "Institution Student"


@pytest.mark.asyncio
async def test_registration_rejects_institution_incompatible_with_cohort_or_department(client):
    http, _ = client
    student = await http.post("/api/v1/auth/register/student", json={
        "email": "wrong-student@example.test", "password": "institution-aware password 42",
        "full_name": "Wrong Institution Student", "institution_id": "institution-2",
        "enrollment_number": "WRONG-ENR-01", "cohort_id": "cohort-1",
    })
    assert student.status_code == 422
    assert "cohort" in student.json()["detail"].lower()

    faculty = await http.post("/api/v1/auth/register/faculty", json={
        "email": "wrong-faculty@example.test", "password": "institution-aware password 42",
        "full_name": "Wrong Institution Faculty", "institution_id": "institution-2",
        "employee_code": "WRONG-EMP-01", "department_id": "department-1", "designation": "Lecturer",
    })
    assert faculty.status_code == 422
    assert "department" in faculty.json()["detail"].lower()

@pytest.mark.asyncio
async def test_faculty_verification_does_not_bypass_approval(client):
    http, sent_tokens = client
    signup = await http.post("/api/v1/auth/register/faculty", json={
        "email": "faculty@example.com",
        "password": "a secure faculty password 42",
        "full_name": "Faculty One",
        "institution_id": "institution-1",
        "employee_code": "FAC-001",
        "department_id": "department-1",
        "designation": "Lecturer",
    })
    assert signup.status_code == 201
    assert signup.json()["activation_pending"] is True

    verified = await http.post("/api/v1/auth/verify-email", json={
        "token": sent_tokens["faculty@example.com"],
    })
    assert verified.status_code == 200
    assert "approval" in verified.json()["message"].lower()

    login = await http.post("/api/v1/auth/login", json={
        "email": "faculty@example.com",
        "password": "a secure faculty password 42",
    })
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_email_and_enrollment_are_rejected_atomically(client):
    http, _ = client
    payload = {
        "email": "first@example.com",
        "password": "a secure student password 42",
        "full_name": "Student One",
        "enrollment_number": "ENR-DUP",
        "cohort_id": "cohort-1",
    }
    assert (await http.post("/api/v1/auth/register/student", json=payload)).status_code == 201

    duplicate_email = await http.post("/api/v1/auth/register/student", json=payload)
    assert duplicate_email.status_code == 409

    duplicate_number = await http.post("/api/v1/auth/register/student", json={
        **payload,
        "email": "second@example.com",
    })
    assert duplicate_number.status_code == 409

    missing_auth = await http.get("/api/v1/students/me")
    assert missing_auth.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_is_single_use_and_revokes_old_access_tokens(client, monkeypatch):
    http, verification_tokens = client
    reset_tokens = {}

    async def fake_send_reset(email: str, token: str) -> None:
        reset_tokens[email] = token

    monkeypatch.setattr(auth_module, "send_password_reset_email", fake_send_reset)
    signup = await http.post("/api/v1/auth/register/student", json={
        "email": "reset@example.com",
        "password": "original secure password 42",
        "full_name": "Reset User",
        "enrollment_number": "ENR-RESET",
        "cohort_id": "cohort-1",
    })
    assert signup.status_code == 201
    assert (await http.post("/api/v1/auth/verify-email", json={"token": verification_tokens["reset@example.com"]})).status_code == 200
    login = await http.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "original secure password 42"})
    old_token = login.json()["access_token"]

    request = await http.post("/api/v1/auth/password-reset/request", json={"email": "reset@example.com"})
    assert request.status_code == 200
    reset_token = reset_tokens["reset@example.com"]
    changed = await http.post("/api/v1/auth/password-reset/confirm", json={
        "token": reset_token, "new_password": "new secure password 2026",
    })
    assert changed.status_code == 200
    assert (await http.get("/api/v1/students/me", headers={"Authorization": f"Bearer {old_token}"})).status_code == 401
    assert (await http.post("/api/v1/auth/password-reset/confirm", json={
        "token": reset_token, "new_password": "another secure password 2026",
    })).status_code == 400
    assert (await http.post("/api/v1/auth/login", json={
        "email": "reset@example.com", "password": "original secure password 42",
    })).status_code == 401
    new_login = await http.post("/api/v1/auth/login", json={
        "email": "reset@example.com", "password": "new secure password 2026",
    })
    assert new_login.status_code == 200
    assert (await http.get("/api/v1/students/me", headers={
        "Authorization": f"Bearer {new_login.json()['access_token']}",
    })).status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_all_previously_issued_access_tokens(client):
    http, verification_tokens = client
    signup = await http.post("/api/v1/auth/register/student", json={
        "email": "logout@example.com",
        "password": "secure logout password 42",
        "full_name": "Logout User",
        "enrollment_number": "ENR-LOGOUT",
        "cohort_id": "cohort-1",
    })
    assert signup.status_code == 201
    assert (await http.post("/api/v1/auth/verify-email", json={"token": verification_tokens["logout@example.com"]})).status_code == 200
    login = await http.post("/api/v1/auth/login", json={"email": "logout@example.com", "password": "secure logout password 42"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await http.get("/api/v1/students/me", headers=headers)).status_code == 200
    assert (await http.post("/api/v1/auth/logout", headers=headers)).status_code == 200
    assert (await http.get("/api/v1/students/me", headers=headers)).status_code == 401
