from datetime import date, timedelta
import importlib

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.dependencies import get_current_account
from app.core.database import get_db_session
from app.main import app
from app.models import (
    Account, AccountRole, Base, Cohort, Department, FacultyProfile, Institution,
    InternshipApplication, InternshipOpportunity, InternshipPlacement,
    InternshipProvider, InternshipWorkLog, InternshipWorkLogReview,
    Role, School, StudentProfile,
)
from app.models.employers import EmployerMembership, EmployerOrganization


@pytest_asyncio.fixture
async def persisted_role_workflow():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        # The legacy identity lookup for industry-mentor profiles is a deployed
        # table not currently represented by a SQLAlchemy model.
        await connection.exec_driver_sql(
            "CREATE TABLE industry_mentors "
            "(id INTEGER PRIMARY KEY, account_id VARCHAR(36) NOT NULL UNIQUE, status VARCHAR(20) NOT NULL)"
        )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    accounts = {
        "owner1": Account(id="owner1", email="owner1@company.test", password_hash="x", full_name="Owner One", is_active=True, is_verified=True),
        "owner2": Account(id="owner2", email="owner2@company.test", password_hash="x", full_name="Owner Two", is_active=True, is_verified=True),
        "student1": Account(id="student1", email="student1@campus.test", password_hash="x", full_name="Student One", is_active=True, is_verified=True),
        "student2": Account(id="student2", email="student2@campus.test", password_hash="x", full_name="Student Two", is_active=True, is_verified=True),
        "faculty1": Account(id="faculty1", email="faculty1@campus.test", password_hash="x", full_name="Faculty One", is_active=True, is_verified=True),
        "faculty2": Account(id="faculty2", email="faculty2@campus.test", password_hash="x", full_name="Faculty Two", is_active=True, is_verified=True),
        "mentor1": Account(id="mentor1", email="mentor1@company.test", password_hash="x", full_name="Mentor One", is_active=True, is_verified=True),
        "mentor2": Account(id="mentor2", email="mentor2@company.test", password_hash="x", full_name="Mentor Two", is_active=True, is_verified=True),
    }
    async with factory() as session:
        session.add_all(accounts.values())
        await session.flush()

        institution = Institution(
            id="institution", name="Example Institute", slug="example-institute",
            status="ACTIVE", created_by_account_id="owner1",
        )
        school = School(
            id="school", code="SCH", name="Example School",
            institution_id=institution.id, is_active=True, status="ACTIVE",
        )
        departments = [
            Department(id="dept1", school_id=school.id, code="D1", name="Department One", is_active=True, status="ACTIVE"),
            Department(id="dept2", school_id=school.id, code="D2", name="Department Two", is_active=True, status="ACTIVE"),
        ]
        roles = [
            Role(id="role-student", name="STUDENT"),
            Role(id="role-faculty", name="FACULTY"),
            Role(id="role-industry", name="INDUSTRY_MENTOR"),
        ]
        session.add_all([institution, school, *departments, *roles])
        await session.flush()
        profiles = [
            StudentProfile(id=101, student_id=501, account_id="student1", enrollment_number="ENR-001", department_id="dept1", current_semester=7),
            StudentProfile(id=102, student_id=502, account_id="student2", enrollment_number="ENR-002", department_id="dept2", current_semester=7),
            FacultyProfile(id=11, account_id="faculty1", employee_number="F-001", employee_code="F-001", display_name="Faculty One", department_id="dept1", designation="Mentor", employment_status="active"),
            FacultyProfile(id=22, account_id="faculty2", employee_number="F-002", employee_code="F-002", display_name="Faculty Two", department_id="dept2", designation="Mentor", employment_status="active"),
        ]
        session.add_all(profiles)
        role_map = {role.name: role.id for role in roles}
        session.add_all([
            AccountRole(account_id="student1", role_id=role_map["STUDENT"]),
            AccountRole(account_id="student2", role_id=role_map["STUDENT"]),
            AccountRole(account_id="faculty1", role_id=role_map["FACULTY"]),
            AccountRole(account_id="faculty2", role_id=role_map["FACULTY"]),
            AccountRole(account_id="mentor1", role_id=role_map["INDUSTRY_MENTOR"]),
            AccountRole(account_id="mentor2", role_id=role_map["INDUSTRY_MENTOR"]),
        ])
        organizations = [
            EmployerOrganization(id="org1", legal_name="Company One", display_name="Company One", normalized_name="company one", created_by_account_id="owner1", status="ACTIVE"),
            EmployerOrganization(id="org2", legal_name="Company Two", display_name="Company Two", normalized_name="company two", created_by_account_id="owner2", status="ACTIVE"),
        ]
        session.add_all(organizations)
        await session.flush()
        session.add_all([
            EmployerMembership(id="owner-membership1", organization_id="org1", account_id="owner1", role="OWNER", status="ACTIVE"),
            EmployerMembership(id="owner-membership2", organization_id="org2", account_id="owner2", role="OWNER", status="ACTIVE"),
            EmployerMembership(id="membership1", organization_id="org1", account_id="mentor1", role="INDUSTRY_MENTOR", status="ACTIVE"),
            EmployerMembership(id="membership2", organization_id="org2", account_id="mentor2", role="INDUSTRY_MENTOR", status="ACTIVE"),
        ])
        providers = [
            InternshipProvider(id="provider1", company_name="Company One", employer_organization_id="org1"),
            InternshipProvider(id="provider2", company_name="Company Two", employer_organization_id="org2"),
        ]
        session.add_all(providers)
        await session.flush()
        today = date.today()
        opportunities = [
            InternshipOpportunity(id="job1", provider_id="provider1", title="Placement One", description="First internship", location="Remote", application_deadline=today + timedelta(days=30), is_active=True, lifecycle_status="PUBLISHED"),
            InternshipOpportunity(id="job2", provider_id="provider2", title="Placement Two", description="Second internship", location="Remote", application_deadline=today + timedelta(days=30), is_active=True, lifecycle_status="PUBLISHED"),
        ]
        session.add_all(opportunities)
        await session.flush()
        applications = [
            InternshipApplication(id="application1", opportunity_id="job1", student_id=101, status="OFFERED"),
            InternshipApplication(id="application2", opportunity_id="job2", student_id=102, status="OFFERED"),
        ]
        session.add_all(applications)
        await session.flush()
        session.add_all([
            InternshipPlacement(id="placement1", application_id="application1", student_id=101, faculty_supervisor_id=11, industry_mentor_account_id="mentor1", start_date=today - timedelta(days=7), end_date=today + timedelta(days=30), status="ONGOING"),
            InternshipPlacement(id="placement2", application_id="application2", student_id=102, faculty_supervisor_id=22, industry_mentor_account_id="mentor2", start_date=today - timedelta(days=7), end_date=today + timedelta(days=30), status="ONGOING"),
        ])
        await session.flush()
        connection = await session.connection()
        await connection.exec_driver_sql(
            "INSERT INTO industry_mentors (id, account_id, status) VALUES (201, 'mentor1', 'active'), (202, 'mentor2', 'active')"
        )
        await session.commit()

    selected_account = {"value": accounts["student1"]}

    async def override_db():
        async with factory() as session:
            yield session

    async def override_account():
        return selected_account["value"]

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_account] = override_account
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        yield {
            "client": client, "account": selected_account, "accounts": accounts,
            "session_factory": factory,
        }
    finally:
        await client.aclose()
        app.dependency_overrides.pop(get_current_account, None)
        app.dependency_overrides.pop(get_db_session, None)
        await engine.dispose()


@pytest.mark.asyncio
async def test_persisted_student_faculty_industry_mentor_workflow_is_isolated(persisted_role_workflow, monkeypatch):
    ctx = persisted_role_workflow
    client = ctx["client"]
    notifications = []
    route_module = importlib.import_module("app.modules.internships.router")

    async def fake_notification(**kwargs):
        notifications.append(kwargs)

    monkeypatch.setattr(route_module, "send_work_log_notification", fake_notification)
    today = date.today().isoformat()

    async def create_and_submit(account_id: str, placement_id: str, summary: str) -> str:
        ctx["account"]["value"] = ctx["accounts"][account_id]
        created = await client.post("/api/v1/modules/internships/work-logs", json={
            "placement_id": placement_id, "work_date": today,
            "summary": summary, "tasks_completed": "Completed assigned project tasks",
            "skills_used": "Python and SQL", "learning_outcomes": "Improved data analysis",
            "next_steps": "Document implementation",
        })
        assert created.status_code == 201, created.text
        log_id = created.json()["id"]
        submitted = await client.post(f"/api/v1/modules/internships/work-logs/{log_id}/submit")
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "SUBMITTED"
        notification_status = submitted.json()["notification_status"]
        assert notification_status["status"] == "ACCEPTED_BY_PROVIDER"
        assert notification_status["accepted_by_provider"] == 2
        assert notification_status["failed"] == 0
        return log_id

    log1 = await create_and_submit("student1", "placement1", "Built student analytics")
    log2 = await create_and_submit("student2", "placement2", "Built reporting dashboard")

    async with ctx["session_factory"]() as session:
        stored1 = await session.get(InternshipWorkLog, log1)
        stored2 = await session.get(InternshipWorkLog, log2)
        assert stored1 is not None and stored1.student_id == 101 and stored1.status == "SUBMITTED"
        assert stored2 is not None and stored2.student_id == 102 and stored2.status == "SUBMITTED"

    ctx["account"]["value"] = ctx["accounts"]["faculty1"]
    faculty1_logs = await client.get("/api/v1/modules/internships/work-logs/supervised")
    assert faculty1_logs.status_code == 200
    assert {item["id"] for item in faculty1_logs.json()["items"]} == {log1}
    assert (await client.get(f"/api/v1/modules/internships/work-logs/{log2}")).status_code == 404
    faculty_review = await client.post(f"/api/v1/modules/internships/work-logs/{log1}/review", json={
        "decision": "ACKNOWLEDGED", "feedback": "Good progress; keep the evidence linked.",
    })
    assert faculty_review.status_code == 200, faculty_review.text
    assert faculty_review.json()["work_log"]["status"] == "SUBMITTED"
    assert faculty_review.json()["review"]["reviewer_role"] == "faculty_mentor"
    assert faculty_review.json()["student_notification_status"] == "ACCEPTED_BY_PROVIDER"

    ctx["account"]["value"] = ctx["accounts"]["faculty2"]
    faculty2_logs = await client.get("/api/v1/modules/internships/work-logs/supervised")
    assert faculty2_logs.status_code == 200
    assert {item["id"] for item in faculty2_logs.json()["items"]} == {log2}
    assert (await client.post(f"/api/v1/modules/internships/work-logs/{log1}/review", json={
        "decision": "ACKNOWLEDGED", "feedback": "Should not be allowed",
    })).status_code == 404

    ctx["account"]["value"] = ctx["accounts"]["mentor1"]
    mentor1_logs = await client.get("/api/v1/modules/internships/work-logs/mentor/me")
    assert mentor1_logs.status_code == 200
    assert {item["id"] for item in mentor1_logs.json()["items"]} == {log1}

    ctx["account"]["value"] = ctx["accounts"]["mentor2"]
    mentor2_logs = await client.get("/api/v1/modules/internships/work-logs/mentor/me")
    assert mentor2_logs.status_code == 200
    assert {item["id"] for item in mentor2_logs.json()["items"]} == {log2}
    denied_review = await client.post(f"/api/v1/modules/internships/work-logs/{log1}/mentor-review", json={
        "decision": "ACKNOWLEDGED", "feedback": "Cross-mentor access must fail",
    })
    assert denied_review.status_code == 404

    ctx["account"]["value"] = ctx["accounts"]["mentor1"]
    industry_review = await client.post(f"/api/v1/modules/internships/work-logs/{log1}/mentor-review", json={
        "decision": "ACKNOWLEDGED", "feedback": "Industry review confirms the submitted progress.",
    })
    assert industry_review.status_code == 200, industry_review.text
    assert industry_review.json()["work_log"]["status"] == "REVIEWED"
    assert industry_review.json()["review"]["reviewer_role"] == "INDUSTRY_MENTOR"
    assert industry_review.json()["student_notification_status"] == "ACCEPTED_BY_PROVIDER"

    ctx["account"]["value"] = ctx["accounts"]["student1"]
    review_history = await client.get(f"/api/v1/modules/internships/work-logs/{log1}/reviews")
    assert review_history.status_code == 200
    reviews = review_history.json()["items"]
    assert {item["reviewer_role"] for item in reviews} == {"FACULTY", "INDUSTRY_MENTOR"}
    assert {item["feedback"] for item in reviews} == {
        "Good progress; keep the evidence linked.",
        "Industry review confirms the submitted progress.",
    }
    my_logs = await client.get("/api/v1/modules/internships/work-logs/me")
    assert my_logs.status_code == 200
    student_log = next(item for item in my_logs.json()["items"] if item["id"] == log1)
    assert student_log["status"] == "REVIEWED"
    assert len(student_log["reviews"]) == 2

    ctx["account"]["value"] = ctx["accounts"]["student2"]
    assert (await client.get(f"/api/v1/modules/internships/work-logs/{log1}")).status_code == 404
    assert (await client.get(f"/api/v1/modules/internships/work-logs/{log1}/reviews")).status_code == 404
    assert (await client.patch(f"/api/v1/modules/internships/work-logs/{log1}", json={
        "placement_id": "placement1", "work_date": today,
        "summary": "Attempt to overwrite", "tasks_completed": "Try changing another student record",
    })).status_code == 404

    async with ctx["session_factory"]() as session:
        stored1 = await session.get(InternshipWorkLog, log1)
        rows = list((await session.execute(select(InternshipWorkLogReview))).scalars().all())
        reviews_for_log1 = [item for item in rows if str(item.work_log_id) == log1]
        assert stored1 is not None and stored1.status == "REVIEWED"
        assert len(reviews_for_log1) == 2
        assert {item.reviewer_account_id for item in reviews_for_log1} == {"faculty1", "mentor1"}
        assert len({item["idempotency_key"] for item in notifications}) == len(notifications)
        assert {item["to"] for item in notifications} >= {
            "faculty1@campus.test", "mentor1@company.test", "faculty2@campus.test",
            "mentor2@company.test", "student1@campus.test",
        }



@pytest.mark.asyncio
async def test_student_application_is_scoped_to_owning_recruiter_and_status_syncs(persisted_role_workflow):
    ctx = persisted_role_workflow
    client = ctx["client"]
    job_id = "job3"

    async with ctx["session_factory"]() as session:
        session.add(InternshipOpportunity(
            id=job_id, provider_id="provider1", title="Data Science Internship",
            description="Build data pipelines and analytical products for students.",
            location="Remote", application_deadline=date.today() + timedelta(days=30),
            is_active=True, lifecycle_status="PUBLISHED", opportunity_type="INTERNSHIP",
            employment_type="INTERNSHIP", work_mode="REMOTE", created_by_account_id="owner1",
        ))
        await session.commit()

    # Student applies through the actual mounted application endpoint.
    ctx["account"]["value"] = ctx["accounts"]["student1"]
    applied = await client.post(f"/api/v1/internships/opportunities/{job_id}/applications")
    assert applied.status_code == 201, applied.text
    application_id = applied.json()["id"]
    assert applied.json()["status"] == "APPLIED"

    async with ctx["session_factory"]() as session:
        stored = await session.get(InternshipApplication, application_id)
        assert stored is not None
        assert stored.student_id == 101
        assert stored.opportunity_id == job_id
        assert stored.recruitment_stage == "SUBMITTED"

    # The owning recruiter can list and inspect the private candidate record.
    ctx["account"]["value"] = ctx["accounts"]["owner1"]
    listed = await client.get("/api/v1/employers/organizations/org1/applications")
    assert listed.status_code == 200, listed.text
    item = next(row for row in listed.json()["items"] if row["id"] == application_id)
    assert item["applicant_name"] == "Student One"
    assert item["stage"] == "SUBMITTED"

    detail = await client.get(
        f"/api/v1/employers/organizations/org1/applications/{application_id}"
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["applicant"]["email"] == "student1@campus.test"

    # A second organization cannot see or mutate this application, even when
    # it supplies a valid application UUID belonging to the first organization.
    ctx["account"]["value"] = ctx["accounts"]["owner2"]
    other_list = await client.get("/api/v1/employers/organizations/org2/applications")
    assert other_list.status_code == 200, other_list.text
    assert application_id not in {row["id"] for row in other_list.json()["items"]}
    denied_read = await client.get(
        f"/api/v1/employers/organizations/org2/applications/{application_id}"
    )
    assert denied_read.status_code == 404
    denied_write = await client.post(
        f"/api/v1/employers/organizations/org2/applications/{application_id}/stage",
        json={"stage": "UNDER_REVIEW", "note": "Unauthorized cross-organization attempt"},
    )
    assert denied_write.status_code == 404

    async with ctx["session_factory"]() as session:
        unchanged = await session.get(InternshipApplication, application_id)
        assert unchanged is not None
        assert unchanged.recruitment_stage == "SUBMITTED"
        assert unchanged.status == "APPLIED"

    # The owning recruiter advances the real persisted state and the student
    # sees the allowed status update through their own application list.
    ctx["account"]["value"] = ctx["accounts"]["owner1"]
    under_review = await client.post(
        f"/api/v1/employers/organizations/org1/applications/{application_id}/stage",
        json={"stage": "UNDER_REVIEW", "note": "Initial review completed"},
    )
    assert under_review.status_code == 200, under_review.text
    assert under_review.json()["stage"] == "UNDER_REVIEW"

    shortlisted = await client.post(
        f"/api/v1/employers/organizations/org1/applications/{application_id}/stage",
        json={"stage": "SHORTLISTED", "note": "Candidate shortlisted"},
    )
    assert shortlisted.status_code == 200, shortlisted.text
    assert shortlisted.json()["stage"] == "SHORTLISTED"
    assert shortlisted.json()["legacy_status"] == "SHORTLISTED"

    ctx["account"]["value"] = ctx["accounts"]["student1"]
    my_applications = await client.get("/api/v1/internships/applications/me")
    assert my_applications.status_code == 200, my_applications.text
    student_view = next(row for row in my_applications.json()["items"] if row["id"] == application_id)
    assert student_view["status"] == "SHORTLISTED"

    async with ctx["session_factory"]() as session:
        persisted = await session.get(InternshipApplication, application_id)
        assert persisted is not None
        assert persisted.status == "SHORTLISTED"
        assert persisted.recruitment_stage == "SHORTLISTED"
