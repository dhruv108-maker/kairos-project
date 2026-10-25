from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import (
    Account, AcademicYear, Base, Cohort, Department, FacultyProfile, Institution,
    InstitutionMembership, Programme, School, StudentAcademicRecord, StudentProfile,
)
from app.modules.academics.admin_service import AcademicAdminError, AcademicAdminService
from app.modules.audit.service import AuditService


@pytest_asyncio.fixture
async def academic_admin_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        admin = Account(id="admin", email="admin@example.test", password_hash="x", full_name="Admin", is_active=True, is_verified=True)
        student_account = Account(id="student-account", email="student@example.test", password_hash="x", full_name="Student", is_active=True, is_verified=True)
        faculty_account = Account(id="faculty-account", email="faculty@example.test", password_hash="x", full_name="Faculty", is_active=True, is_verified=True)
        institution = Institution(id="institution", name="Institute", slug="institute", status="ACTIVE", created_by_account_id="admin")
        school = School(id="school", institution_id="institution", code="SCH", name="School", is_active=True)
        department = Department(id="department", school_id="school", code="DEP", name="Department", is_active=True)
        programme = Programme(id="programme", department_id="department", code="PROG", name="Programme", degree_level="UG", duration_years=3, is_active=True)
        year = AcademicYear(id="year", institution_id="institution", year_label="2026-27", start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), is_current=True)
        cohort = Cohort(id="cohort", programme_id="programme", academic_year_id="year", name="Batch", graduation_year=2029)
        student = StudentProfile(id=1, student_id=101, account_id="student-account", enrollment_number="E-1", department_id="department", cohort_id="cohort", current_semester=1)
        faculty = FacultyProfile(id=1, account_id="faculty-account", employee_code="F-1", display_name="Faculty", department_id="department", designation="Mentor")
        record = StudentAcademicRecord(id="record", student_profile_id=1, institution_name="Prior School", qualification="Diploma")
        db.add_all([admin, student_account, faculty_account, institution, school, department, programme, year, cohort, student, faculty, record])
        await db.flush()
        db.add(InstitutionMembership(institution_id="institution", account_id="admin", role="INSTITUTION_ADMIN", status="ACTIVE"))
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_can_search_students_and_verify_academic_records(academic_admin_session):
    service = AcademicAdminService(academic_admin_session)
    student = await academic_admin_session.get(StudentProfile, 1)
    student.cohort_id = None
    await academic_admin_session.commit()
    rows = await service.list_students("institution", "admin", "E-1", 50, 0)
    assert len(rows) == 1
    assert rows[0][0].id == 1
    record = await service.verify_academic_record("institution", "admin", 1, "record", True)
    assert record.is_verified is True
    assert record.verified_by_account_id == "admin"
    assert record.verified_at is not None
    events = await AuditService(academic_admin_session).list_for_institution("institution", "admin", 20, 0)
    assert any(event.action == "student.academic_record_verification_changed" for event in events)


@pytest.mark.asyncio
async def test_student_cannot_be_assigned_a_cohort_from_another_institution(academic_admin_session):
    db = academic_admin_session
    db.add(Institution(id="other-institution", name="Other", slug="other", status="ACTIVE", created_by_account_id="admin"))
    db.add(School(id="other-school", institution_id="other-institution", code="OTH", name="Other School", is_active=True))
    db.add(Department(id="other-department", school_id="other-school", code="OTHDEP", name="Other Department", is_active=True))
    db.add(Programme(id="other-programme", department_id="other-department", code="OTHERPROG", name="Other Programme", degree_level="UG", duration_years=3, is_active=True))
    db.add(AcademicYear(id="other-year", institution_id="other-institution", year_label="OTHER-2026", start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), is_current=False))
    db.add(Cohort(id="other-cohort", programme_id="other-programme", academic_year_id="other-year", name="Other Batch", graduation_year=2029))
    await db.commit()
    service = AcademicAdminService(db)
    with pytest.raises(AcademicAdminError) as error:
        await service.change_student_cohort("institution", "admin", 1, "other-cohort", None)
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_student_cannot_have_two_active_mentors(academic_admin_session):
    service = AcademicAdminService(academic_admin_session)
    item = await service.create_mentorship("institution", "admin", 1, 1)
    assert item.status == "active"
    with pytest.raises(AcademicAdminError) as error:
        await service.create_mentorship("institution", "admin", 1, 1)
    assert error.value.status_code == 409


from app.modules.analytics.service import AnalyticsService


@pytest.mark.asyncio
async def test_role_scoped_dashboards_use_persisted_counts(academic_admin_session):
    service = AnalyticsService(academic_admin_session)
    student = await service.student_dashboard("student-account")
    assert student["internships"] == {"applications": 0, "placements": 0}
    assert student["reports"]["total"] == 0
    faculty = await service.faculty_dashboard("faculty-account")
    assert faculty["placements_supervised"] == 0
    admin = await service.institution_dashboard("institution", "admin")
    assert admin["students"] == 1
    assert admin["faculty"] == 1
    assert admin["schools"] == 1
    assert admin["departments"] == 1


from app.modules.organizations.service import OrganizationService, OrganizationWorkflowError


@pytest.mark.asyncio
async def test_assessment_assignment_enforces_persisted_lifecycle_transitions(academic_admin_session):
    service = OrganizationService(academic_admin_session)
    campaign = await service.create_campaign(
        "institution", "admin", "Review campaign", None,
        date(2026, 10, 1), date(2026, 12, 1),
    )
    assignment = await service.assign_faculty(
        "institution", "admin", campaign.id, "faculty-account", "MANUAL"
    )
    assert assignment.assignment_status == "assigned"

    started = await service.update_assignment(
        "institution", "faculty-account", campaign.id, str(assignment.id), "started"
    )
    assert started.assignment_status == "started"

    with pytest.raises(OrganizationWorkflowError) as invalid_transition:
        await service.update_assignment(
            "institution", "faculty-account", campaign.id, str(assignment.id), "approved"
        )
    assert invalid_transition.value.status_code == 409
    persisted = await academic_admin_session.get(type(assignment), assignment.id)
    assert persisted.assignment_status == "started"

    submitted = await service.update_assignment(
        "institution", "faculty-account", campaign.id, str(assignment.id), "submitted"
    )
    assert submitted.assignment_status == "submitted"
