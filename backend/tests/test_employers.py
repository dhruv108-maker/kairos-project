from datetime import date, timedelta
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Account, Base
from app.models.employers import EmployerMembership
from app.models.internship import InternshipProvider
from app.modules.employers.service import EmployerService, EmployerError


@pytest_asyncio.fixture
async def employer_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(Account(id="owner", email="owner@example.test", password_hash="x", full_name="Owner", is_active=True, is_verified=True))
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_creates_owner_and_legacy_provider(employer_session):
    item = await EmployerService(employer_session).register("owner", {
        "legal_name": "Example Works", "display_name": "Example", "organization_type": "COMPANY"
    })
    member = (await employer_session.execute(select(EmployerMembership).where(EmployerMembership.organization_id == item.id, EmployerMembership.account_id == "owner"))).scalar_one()
    provider = (await employer_session.execute(select(InternshipProvider).where(InternshipProvider.employer_organization_id == item.id))).scalar_one()
    assert item.status == "PENDING_VERIFICATION"
    assert member.role == "OWNER" and member.status == "ACTIVE"
    assert provider.company_name == "Example"


@pytest.mark.asyncio
async def test_nonmember_cannot_access_employer_jobs(employer_session):
    item = await EmployerService(employer_session).register("owner", {"legal_name": "Example Works", "display_name": "Example"})
    with pytest.raises(EmployerError) as error:
        await EmployerService(employer_session).list_jobs(item.id, "other", 20, 0)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_pending_employer_cannot_publish_job(employer_session):
    service = EmployerService(employer_session)
    org = await service.register("owner", {"legal_name": "Example Works", "display_name": "Example"})
    job = await service.create_job(org.id, "owner", {
        "title": "Backend Intern", "description": "Build APIs and automated tests for Kairos.",
        "location": "Remote", "application_deadline": date.today() + timedelta(days=10)
    })
    with pytest.raises(EmployerError) as error:
        await service.transition_job(org.id, "owner", job.id, "publish")
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_employer_invitation_is_single_use_and_email_bound(employer_session, monkeypatch):
    from app.modules.employers import service as employer_service_module
    from app.models.employers import EmployerInvitation
    from sqlalchemy import select

    sent = []
    async def fake_send(email, subject, message):
        sent.append((email, subject, message))
    monkeypatch.setattr(employer_service_module, "send_workflow_notification", fake_send)

    service = EmployerService(employer_session)
    org = await service.register("owner", {"legal_name": "Invitation Labs", "display_name": "Invitation Labs"})
    invitation, delivery_sent = await service.invite_member(org.id, "owner", "recruiter@example.test", "RECRUITER")
    assert delivery_sent is True
    token = sent[0][2].split("token=", 1)[1]
    recruiter = __import__("app.models.academic", fromlist=["Account"]).Account(
        id="recruiter", email="recruiter@example.test", password_hash="x",
        full_name="Recruiter", is_active=True, is_verified=True,
    )
    employer_session.add(recruiter)
    await employer_session.commit()

    accepted = await service.accept_invitation("recruiter", token)
    assert accepted.role == "RECRUITER"
    with pytest.raises(EmployerError) as error:
        await service.accept_invitation("recruiter", token)
    assert error.value.status_code == 400
    stored = await employer_session.scalar(select(EmployerInvitation).where(EmployerInvitation.id == invitation.id))
    assert stored.accepted_at is not None


@pytest.mark.asyncio
async def test_only_active_company_profiles_are_public(employer_session):
    from app.models.academic import AccountRole, Role
    service = EmployerService(employer_session)
    org = await service.register("owner", {"legal_name": "Public Profile Ltd", "display_name": "Public Profile"})
    with pytest.raises(EmployerError) as error:
        await service.public_company(org.id)
    assert error.value.status_code == 404

    await service.submit_verification(org.id, "owner")
    role = Role(id="platform-role-public", name="PLATFORM_ADMIN")
    employer_session.add(role)
    employer_session.add(AccountRole(account_id="owner", role_id=role.id))
    await employer_session.commit()
    await service.set_organization_status(org.id, "owner", "ACTIVE", "Reviewed")
    assert (await service.public_company(org.id)).status == "ACTIVE"
    await service.set_organization_status(org.id, "owner", "SUSPENDED", "Policy review")
    with pytest.raises(EmployerError) as suspended:
        await service.public_company(org.id)
    assert suspended.value.status_code == 404



@pytest.mark.asyncio
async def test_recruiter_cannot_read_or_modify_another_organizations_job(employer_session):
    from app.models.academic import Account
    from app.models.internship import InternshipOpportunity

    db = employer_session
    db.add(Account(
        id="other-owner",
        email="other-owner@example.test",
        password_hash="x",
        full_name="Other Owner",
        is_active=True,
        is_verified=True,
    ))
    await db.commit()

    service = EmployerService(db)
    own_org = await service.register(
        "owner", {"legal_name": "First Company", "display_name": "First Company"}
    )
    other_org = await service.register(
        "other-owner", {"legal_name": "Second Company", "display_name": "Second Company"}
    )
    other_job = await service.create_job(other_org.id, "other-owner", {
        "title": "Private Backend Role",
        "description": "This listing belongs to the second company.",
        "location": "Remote",
        "application_deadline": date.today() + timedelta(days=10),
    })

    # The denial deliberately hides whether the supplied job ID exists in another org.
    with pytest.raises(EmployerError) as read_error:
        await service.get_owned_job(own_org.id, "owner", other_job.id)
    assert read_error.value.status_code == 404

    with pytest.raises(EmployerError) as write_error:
        await service.update_job(own_org.id, "owner", other_job.id, {"title": "Hijacked"})
    assert write_error.value.status_code == 404

    persisted = await db.get(InternshipOpportunity, other_job.id)
    assert persisted is not None
    assert persisted.title == "Private Backend Role"
