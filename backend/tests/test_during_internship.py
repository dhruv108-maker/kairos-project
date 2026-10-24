from datetime import date

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import (
    Account, AccountRole, AcademicYear, Base, Cohort, Department, FacultyProfile,
    InternshipApplication, InternshipOpportunity, InternshipPlacement, InternshipProvider,
    Programme, Role, School, StudentProfile,
)
from app.modules.internships.during_router import (
    WorkLogCreate, WorkLogPatch, WorkLogReviewCreate,
    create_work_log, placement_work_logs, review_work_log, submit_work_log, update_work_log,
)


@pytest_asyncio.fixture
async def during_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        student_account = Account(
            id="student-account", email="student@example.test", password_hash="x",
            full_name="Student Example", is_active=True, is_verified=True,
        )
        other_student_account = Account(
            id="other-student-account", email="other@example.test", password_hash="x",
            full_name="Other Student", is_active=True, is_verified=True,
        )
        faculty_account = Account(
            id="faculty-account", email="faculty@example.test", password_hash="x",
            full_name="Faculty Example", is_active=True, is_verified=True,
        )
        student_role = Role(id="role-student", name="STUDENT")
        faculty_role = Role(id="role-faculty", name="FACULTY")
        school = School(id="school", code="SCH", name="School", is_active=True)
        department = Department(id="department", school_id="school", code="DEP", name="Department", is_active=True)
        programme = Programme(id="programme", department_id="department", code="PROG", name="Programme", is_active=True)
        year = AcademicYear(
            id="year", year_label="2026-27", start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31), is_current=True,
        )
        cohort = Cohort(
            id="cohort", programme_id="programme", academic_year_id="year",
            name="Batch", graduation_year=2029,
        )
        student = StudentProfile(
            id=1, student_id=1001, account_id="student-account",
            enrollment_number="E-1", cohort_id="cohort", current_semester=5,
        )
        other_student = StudentProfile(
            id=2, student_id=1002, account_id="other-student-account",
            enrollment_number="E-2", cohort_id="cohort", current_semester=5,
        )
        faculty = FacultyProfile(
            id="faculty", account_id="faculty-account", employee_code="F-1",
            department_id="department", designation="Mentor",
        )
        provider = InternshipProvider(id="provider", company_name="Example Company")
        opportunity = InternshipOpportunity(
            id="opportunity", provider_id="provider", title="Data Intern", description="Project work",
            location="Vadodara", stipend_amount=0, application_deadline=date(2026, 12, 1), is_active=True,
        )
        application = InternshipApplication(
            id="application", opportunity_id="opportunity", student_id=1, status="OFFERED",
        )
        placement = InternshipPlacement(
            id="placement", application_id="application", student_id=1, faculty_supervisor_id="faculty",
            start_date=date(2026, 10, 1), end_date=date(2026, 12, 31), status="ONGOING",
        )
        db.add_all([
            student_account, other_student_account, faculty_account, student_role, faculty_role,
            AccountRole(account_id="student-account", role_id="role-student"),
            AccountRole(account_id="other-student-account", role_id="role-student"),
            AccountRole(account_id="faculty-account", role_id="role-faculty"),
            school, department, programme, year, cohort, student, other_student, faculty,
            provider, opportunity, application, placement,
        ])
        await db.commit()
        yield db, student_account, other_student_account, faculty_account
    await engine.dispose()


@pytest.mark.asyncio
async def test_work_log_submission_and_revision_flow_is_persisted(during_session):
    db, student_account, _, faculty_account = during_session
    log = await create_work_log(
        "placement",
        WorkLogCreate(
            work_date=date(2026, 10, 21),
            work_summary="Completed data validation and wrote unit tests.",
            duration_minutes=240,
            skills_used=["Python", "SQL"],
        ),
        student_account,
        db,
    )
    assert log["status"] == "DRAFT"
    assert log["skills_used"] == ["Python", "SQL"]

    submitted = await submit_work_log(log["id"], student_account, db)
    assert submitted["status"] == "SUBMITTED"
    assert submitted["submitted_at"] is not None

    review = await review_work_log(
        log["id"],
        WorkLogReviewCreate(decision="REVISION_REQUIRED", feedback="Add the validation results and edge cases."),
        faculty_account,
        db,
    )
    assert review["reviewer_role"] == "FACULTY"
    assert review["decision"] == "REVISION_REQUIRED"

    updated = await update_work_log(
        log["id"],
        WorkLogPatch(work_summary="Completed data validation, added tests, and documented edge cases."),
        student_account,
        db,
    )
    assert updated["status"] == "DRAFT"
    assert len(updated["reviews"]) == 1
    assert updated["reviews"][0]["feedback"] == "Add the validation results and edge cases."


@pytest.mark.asyncio
async def test_student_cannot_read_another_students_placement_logs(during_session):
    db, _, other_student_account, _ = during_session
    with pytest.raises(HTTPException) as error:
        await placement_work_logs("placement", other_student_account, db)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_work_log_cannot_be_created_outside_placement_dates(during_session):
    db, student_account, _, _ = during_session
    with pytest.raises(HTTPException) as error:
        await create_work_log(
            "placement",
            WorkLogCreate(work_date=date(2027, 1, 1), work_summary="Outside placement dates."),
            student_account,
            db,
        )
    assert error.value.status_code == 422


def test_work_log_review_requires_nonblank_feedback():
    with pytest.raises(ValueError):
        WorkLogReviewCreate(decision="COMMENTED", feedback="   ")
