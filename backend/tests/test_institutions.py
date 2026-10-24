from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Account, Base, Department, Institution, InstitutionMembership, School
from app.modules.institutions.service import InstitutionAccessError, InstitutionService


@pytest_asyncio.fixture
async def institution_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        account = Account(id="actor", email="admin@example.test", password_hash="x", full_name="Admin", is_active=True, is_verified=True)
        other_account = Account(id="other", email="other@example.test", password_hash="x", full_name="Other", is_active=True, is_verified=True)
        one = Institution(id="inst-one", name="Institution One", slug="institution-one", status="ACTIVE", created_by_account_id="actor")
        two = Institution(id="inst-two", name="Institution Two", slug="institution-two", status="ACTIVE", created_by_account_id="other")
        session.add_all([account, other_account, one, two])
        await session.flush()
        session.add_all([
            InstitutionMembership(institution_id=one.id, account_id=account.id, role="INSTITUTION_ADMIN", status="ACTIVE"),
            School(id="school-one", institution_id=one.id, code="ONE", name="School One", is_active=True),
            School(id="school-two", institution_id=two.id, code="TWO", name="School Two", is_active=True),
        ])
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_school_listing_is_scoped_to_active_membership(institution_session):
    service = InstitutionService(institution_session)
    schools = await service.list_schools("inst-one", "actor")
    assert [school.id for school in schools] == ["school-one"]


@pytest.mark.asyncio
async def test_cross_institution_parent_reference_is_rejected(institution_session):
    service = InstitutionService(institution_session)
    with pytest.raises(InstitutionAccessError) as error:
        await service.create_department("inst-one", "actor", "school-two", "CROSS", "Cross Tenant")
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_revoked_membership_loses_access(institution_session):
    service = InstitutionService(institution_session)
    member = await service.membership("inst-one", "actor")
    member.status = "REVOKED"
    await institution_session.commit()
    with pytest.raises(InstitutionAccessError) as error:
        await service.list_schools("inst-one", "actor")
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_academic_entities_support_updates_and_safe_deletion(institution_session):
    service = InstitutionService(institution_session)
    await service.create_department("inst-one", "actor", "school-one", "DEP", "Department")
    updated = await service.update_school("inst-one", "actor", "school-one", None, "Updated School", False)
    assert updated.name == "Updated School"
    assert updated.is_active is False
    with pytest.raises(InstitutionAccessError) as error:
        await service.delete_school("inst-one", "actor", "school-one")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_self_service_institution_registration_waits_for_platform_approval(institution_session):
    from app.models.academic import AccountRole, Role
    from app.modules.institutions.service import InstitutionService

    service = InstitutionService(institution_session)
    institution = await service.register_institution("actor", {
        "name": "New Institute", "slug": "new-institute", "institution_type": "COLLEGE",
        "contact_email": "registrar@example.test", "country": "India", "city": "Ahmedabad",
    })
    assert institution.status == "PENDING_APPROVAL"
    membership = await institution_session.get(InstitutionMembership, (institution.id, "actor"))
    assert membership.role == "INSTITUTION_ADMIN"
    assert membership.status == "PENDING"
    with pytest.raises(InstitutionAccessError) as error:
        await service.membership(institution.id, "actor")
    assert error.value.status_code == 403

    platform_role = Role(id="platform-admin-role", name="PLATFORM_ADMIN")
    institution_session.add(platform_role)
    institution_session.add(AccountRole(account_id="other", role_id=platform_role.id))
    await institution_session.commit()
    await service.set_status(institution.id, "other", "ACTIVE")
    membership = await institution_session.get(InstitutionMembership, (institution.id, "actor"))
    assert membership.status == "ACTIVE"
    assert (await service.membership(institution.id, "actor")).role == "INSTITUTION_ADMIN"
