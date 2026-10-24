import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import (
    AcademicYear, Account, Base, Cohort, Department, Programme, School,
    StudentProfile, StudentResume, StorageFile,
)
from app.modules.shared.exceptions import DomainConflictError
from app.modules.student_portfolio.service import StudentPortfolioService


@pytest_asyncio.fixture
async def portfolio_service_session():
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
        profile = StudentProfile(id="student", account_id=account.id, enrollment_number="ENR-1",
                                 cohort_id=cohort.id, current_semester=1)
        storage = StorageFile(id="file", original_name="resume.pdf", file_path="private/resume.pdf",
                              file_size_bytes=100, mime_type="application/pdf", sha256_hash="a" * 64,
                              uploaded_by_account_id=account.id)
        session.add_all([school, department, programme, year, cohort, account, profile, storage])
        await session.commit()
        yield session, profile, account, storage
    await engine.dispose()


@pytest.mark.asyncio
async def test_resume_conflict_rolls_back_and_session_remains_usable(portfolio_service_session):
    session, profile, account, _ = portfolio_service_session
    service = StudentPortfolioService(session)
    await service.create_resume(profile.id, account.id, {
        "storage_file_id": "file", "label": "Primary", "is_primary": True,
    })

    with pytest.raises(DomainConflictError):
        await service.create_resume(profile.id, account.id, {
            "storage_file_id": "file", "label": "Duplicate", "is_primary": True,
        })

    count = await session.scalar(select(func.count()).select_from(StudentResume))
    assert count == 1
    resume = await session.scalar(select(StudentResume))
    assert resume.label == "Primary"
    assert resume.is_primary is True
