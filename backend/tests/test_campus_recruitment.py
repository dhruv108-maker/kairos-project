from datetime import date, timedelta
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import (
    Account, Base, AcademicYear, Cohort, Department, Institution, InstitutionMembership,
    Programme, School, StudentProfile, EmployerOrganization, EmployerMembership,
    InternshipProvider, InternshipOpportunity, RecruitmentDrive, RecruitmentDriveParticipation,
    RecruitmentDriveOpportunity,
)
from app.modules.employers.campus_recruitment_service import CampusRecruitmentService
from app.modules.employers.service import EmployerError
from app.modules.internships.repository import InternshipRepository
from app.main import app


@pytest_asyncio.fixture
async def campus_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add_all([
            Account(id="admin", email="admin@one.test", password_hash="x", full_name="Institution Admin", is_active=True, is_verified=True),
            Account(id="recruiter", email="recruiter@company.test", password_hash="x", full_name="Recruiter", is_active=True, is_verified=True),
            Account(id="student", email="student@one.test", password_hash="x", full_name="Student", is_active=True, is_verified=True),
            Account(id="outsider", email="outsider@two.test", password_hash="x", full_name="Outsider", is_active=True, is_verified=True),
        ])
        session.add_all([
            Institution(id="inst-one", name="One", slug="one", status="ACTIVE", created_by_account_id="admin"),
            Institution(id="inst-two", name="Two", slug="two", status="ACTIVE", created_by_account_id="outsider"),
            EmployerOrganization(id="company", legal_name="Company", display_name="Company", normalized_name="company",
                status="ACTIVE", created_by_account_id="recruiter"),
        ])
        await session.flush()
        session.add_all([
            InstitutionMembership(institution_id="inst-one", account_id="admin", role="INSTITUTION_ADMIN", status="ACTIVE"),
            EmployerMembership(id="membership", organization_id="company", account_id="recruiter", role="RECRUITER", status="ACTIVE"),
            School(id="school-one", institution_id="inst-one", code="S1", name="School One", is_active=True),
            School(id="school-two", institution_id="inst-two", code="S2", name="School Two", is_active=True),
            AcademicYear(id="year-one", institution_id="inst-one", year_label="2026-27", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30)),
        ])
        await session.flush()
        session.add_all([
            Department(id="dep-one", school_id="school-one", code="D1", name="Engineering", is_active=True),
            Department(id="dep-two", school_id="school-two", code="D2", name="Engineering Two", is_active=True),
        ])
        await session.flush()
        session.add_all([
            Programme(id="prog-one", department_id="dep-one", code="P1", name="Computer Science", degree_level="BACHELOR", duration_years=4, is_active=True),
            Programme(id="prog-two", department_id="dep-two", code="P2", name="Other Programme", degree_level="BACHELOR", duration_years=4, is_active=True),
        ])
        await session.flush()
        session.add_all([
            Cohort(id="cohort-one", programme_id="prog-one", academic_year_id="year-one", name="2023", graduation_year=2027),
            Cohort(id="cohort-two", programme_id="prog-two", academic_year_id="year-one", name="2023", graduation_year=2027),
        ])
        await session.flush()
        session.add_all([
            StudentProfile(id=1, student_id=1001, account_id="student", enrollment_number="S-001", cohort_id="cohort-one", current_semester=7),
            StudentProfile(id=2, student_id=1002, account_id="outsider", enrollment_number="S-002", cohort_id="cohort-two", current_semester=7),
            InternshipProvider(id="provider", company_name="Company", employer_organization_id="company"),
        ])
        await session.flush()
        session.add(InternshipOpportunity(id="job", provider_id="provider", title="Software Engineer",
            description="A backend software engineering opportunity.", location="Ahmedabad",
            application_deadline=date.today() + timedelta(days=30), is_active=True, lifecycle_status="PUBLISHED",
            opportunity_type="JOB", employment_type="FULL_TIME", work_mode="HYBRID", openings=1))
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_drive_targets_and_institution_tenant_isolation(campus_session):
    service = CampusRecruitmentService(campus_session)
    drive = await service.create_drive("inst-one", "admin", {
        "name": "2027 Campus Drive", "description": "Graduate hiring",
        "programme_ids": ["prog-one"], "cohort_ids": ["cohort-one"], "graduation_years": [2027],
    })
    assert drive.status == "DRAFT"
    assert (await service.drive_view(drive))["programme_ids"] == ["prog-one"]
    with pytest.raises(EmployerError) as error:
        await service.get_drive(drive.id, "outsider")
    assert error.value.status_code in {403, 404}


@pytest.mark.asyncio
async def test_cross_institution_target_is_rejected(campus_session):
    service = CampusRecruitmentService(campus_session)
    with pytest.raises(EmployerError) as error:
        await service.create_drive("inst-one", "admin", {
            "name": "Bad Target Drive", "description": "Must reject cross-tenant programme",
            "programme_ids": ["prog-two"],
        })
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_eligibility_and_direct_application_guard(campus_session):
    service = CampusRecruitmentService(campus_session)
    drive = RecruitmentDrive(id="drive", institution_id="inst-one", name="Campus 2027",
        description="Campus hiring", status="ACTIVE", created_by_account_id="admin")
    campus_session.add(drive)
    campus_session.add(RecruitmentDriveParticipation(id="participation", drive_id="drive",
        organization_id="company", invited_by_account_id="admin", status="ACCEPTED"))
    campus_session.add(RecruitmentDriveOpportunity(drive_id="drive", opportunity_id="job", added_by_account_id="recruiter"))
    await campus_session.commit()
    result = await service.eligibility("student", "drive", "job")
    assert result["status"] == "eligible"
    await service.apply_guard("student", "job")
    assert await InternshipRepository(campus_session).list_active_opportunities() == []
    result = await service.eligibility("outsider", "drive", "job")
    assert result["status"] == "ineligible"
    assert "INSTITUTION_MISMATCH" in result["reason_codes"]
    with pytest.raises(EmployerError):
        await service.apply_guard("outsider", "job")


def test_campus_recruitment_routes_are_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/institutions/{institution_id}/recruitment-drives" in paths
    assert "/api/v1/recruitment-drives/{drive_id}/employers/{organization_id}" in paths
    assert "/api/v1/students/recruitment-drives/{drive_id}/opportunities" in paths

