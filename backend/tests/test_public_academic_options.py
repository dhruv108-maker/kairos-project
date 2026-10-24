import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Account, Base, Department, Institution, Programme, School
from app.modules.institutions.router import public_academic_options


@pytest_asyncio.fixture
async def academic_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        account = Account(
            id="admin", email="admin@example.test", password_hash="x",
            full_name="Admin", is_active=True, is_verified=True,
        )
        institution = Institution(
            id="12", name="GSFC University", slug="gsfc-university",
            status="ACTIVE", created_by_account_id="admin",
        )
        session.add_all([account, institution])
        await session.flush()
        school = School(
            id="1", institution_id="12", code="SoCIS",
            name="School of Chemical & Industrial Sciences",
            status="active", is_active=True,
        )
        session.add(school)
        await session.flush()
        department = Department(
            id="10", school_id=school.id, code="CHEM",
            name="Chemistry", status="active", is_active=True,
        )
        session.add(department)
        await session.flush()
        session.add(Programme(
            id="100", department_id=department.id, code="BSC-CHEM",
            name="B.Sc. (Hons.) Chemistry", status="active", is_active=True,
        ))
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_public_academic_options_returns_active_institution_hierarchy(academic_session):
    result = await public_academic_options("12", academic_session)

    assert [item["name"] for item in result["schools"]] == [
        "School of Chemical & Industrial Sciences"
    ]
    assert result["departments"][0]["school_id"] == "1"
    assert result["programmes"][0]["department_id"] == "10"
    assert result["cohorts"] == []


@pytest.mark.asyncio
async def test_public_academic_options_does_not_return_other_institution_schools(academic_session):
    other = Institution(
        id="13", name="Other University", slug="other-university",
        status="ACTIVE", created_by_account_id="admin",
    )
    academic_session.add(other)
    await academic_session.flush()
    academic_session.add(School(
        id="2", institution_id="13", code="OTHER",
        name="Other School", status="active", is_active=True,
    ))
    await academic_session.commit()

    result = await public_academic_options("12", academic_session)
    assert [item["id"] for item in result["schools"]] == ["1"]


@pytest.mark.asyncio
async def test_public_academic_options_excludes_inactive_schools(academic_session):
    academic_session.add(School(
        id="3", institution_id="12", code="INACTIVE",
        name="Inactive School", status="inactive", is_active=False,
    ))
    await academic_session.commit()

    result = await public_academic_options("12", academic_session)
    assert [item["id"] for item in result["schools"]] == ["1"]


@pytest.mark.asyncio
async def test_public_academic_options_returns_404_for_inactive_institution(academic_session):
    from fastapi import HTTPException

    institution = await academic_session.get(Institution, "12")
    institution.status = "SUSPENDED"
    await academic_session.commit()

    with pytest.raises(HTTPException) as error:
        await public_academic_options("12", academic_session)
    assert error.value.status_code == 404
