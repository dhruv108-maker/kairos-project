from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import (
    AcademicYear, Account, Base, Cohort, Department, InternshipApplication,
    InternshipOpportunity, InternshipProvider, Programme, School, StudentProfile,
)
from app.modules.internships.exceptions import InvalidInternshipStateTransitionError
from app.modules.internships.repository import InternshipRepository
from app.modules.internships.service import InternshipService


@pytest_asyncio.fixture
async def internship_service_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        school = School(id="school", code="SCH", name="School")
        department = Department(id="department", school_id=school.id, code="CSE", name="Computing")
        programme = Programme(id="programme", department_id=department.id, code="BSC",
                              name="Computer Science", degree_level="undergraduate", duration_years=3)
        year = AcademicYear(id="year", year_label="2026-27", start_date=date(2026, 4, 1),
                            end_date=date(2027, 3, 31), is_current=True)
        cohort = Cohort(id="cohort", programme_id=programme.id, academic_year_id=year.id,
                        name="Batch", graduation_year=2029)
        account = Account(id="account", email="student@example.test", password_hash="unused",
                          full_name="Student", is_active=True, is_verified=True)
        student = StudentProfile(id="student", account_id=account.id, enrollment_number="ENR-1",
                                 cohort_id=cohort.id, current_semester=1)
        provider = InternshipProvider(id="provider", company_name="Example Co")
        opportunity = InternshipOpportunity(
            id="opportunity", provider_id=provider.id, title="Intern", description="Work",
            location="Remote", application_deadline=date(2099, 12, 31), is_active=True,
        )
        application = InternshipApplication(
            id="application", opportunity_id=opportunity.id, student_id=student.id, status="APPLIED",
        )
        session.add_all([school, department, programme, year, cohort, account, student,
                         provider, opportunity, application])
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_invalid_transition_does_not_mutate_application(internship_service_session):
    session = internship_service_session
    service = InternshipService(session)

    with pytest.raises(InvalidInternshipStateTransitionError):
        await service.transition_application("application", "OFFERED")

    application = await session.scalar(select(InternshipApplication).where(
        InternshipApplication.id == "application"
    ))
    assert application.status == "APPLIED"


@pytest.mark.asyncio
async def test_lost_update_rolls_back_without_overwriting_new_state(internship_service_session):
    session = internship_service_session

    class RacingRepository(InternshipRepository):
        async def transition_application(self, application_id, expected_status, new_status):
            # Simulate a concurrent writer changing the row between read and compare-and-set.
            await self.session.execute(
                update(InternshipApplication)
                .where(InternshipApplication.id == application_id)
                .values(status="REJECTED")
            )
            return await super().transition_application(application_id, expected_status, new_status)

    service = InternshipService(session, repository=RacingRepository(session))
    with pytest.raises(InvalidInternshipStateTransitionError, match="concurrently"):
        await service.transition_application("application", "SHORTLISTED")

    # The failed transaction is rolled back rather than leaving half-applied state.
    application = await session.scalar(select(InternshipApplication).where(
        InternshipApplication.id == "application"
    ))
    assert application.status == "APPLIED"
