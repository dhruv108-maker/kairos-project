from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.modules.institutions.invitation_service as invitation_module
from app.models import Account, Base, Department, FacultyProfile, Institution, InstitutionMembership, School
from app.modules.institutions.invitation_service import InstitutionInvitationService, InvitationWorkflowError


@pytest_asyncio.fixture
async def invitation_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        admin = Account(id="admin", email="admin@example.test", password_hash="x", full_name="Admin", is_active=True, is_verified=True)
        faculty_account = Account(id="faculty", email="faculty@example.test", password_hash="x", full_name="Faculty", is_active=True, is_verified=True)
        institution = Institution(id="institution", name="Institute", slug="institute", status="ACTIVE", created_by_account_id="admin")
        school = School(id="school", institution_id="institution", code="SCH", name="School", is_active=True)
        department = Department(id="department", school_id="school", code="DEP", name="Department", is_active=True)
        faculty = FacultyProfile(id=1, account_id="faculty", employee_code="F-1", display_name="Faculty", department_id="department", designation="Mentor")
        db.add_all([admin, faculty_account, institution, school, department, faculty])
        await db.flush()
        db.add(InstitutionMembership(institution_id="institution", account_id="admin", role="INSTITUTION_ADMIN", status="ACTIVE"))
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_invitation_is_hashed_single_use_and_creates_membership(invitation_session, monkeypatch):
    delivered = {}

    async def fake_send(email, institution_name, role, token):
        delivered.update(email=email, role=role, token=token)

    monkeypatch.setattr(invitation_module, "send_institution_invitation_email", fake_send)
    service = InstitutionInvitationService(invitation_session)
    invitation, sent = await service.invite("institution", "admin", "FACULTY@example.test", "FACULTY")
    assert sent is True
    assert invitation.token_hash != delivered["token"]
    membership = await service.accept("faculty", delivered["token"])
    assert membership.role == "FACULTY"
    assert membership.status == "ACTIVE"
    with pytest.raises(InvitationWorkflowError) as error:
        await service.accept("faculty", delivered["token"])
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_invitation_cannot_grant_admin_or_be_accepted_by_another_email(invitation_session, monkeypatch):
    delivered = {}

    async def fake_send(email, institution_name, role, token):
        delivered["token"] = token

    monkeypatch.setattr(invitation_module, "send_institution_invitation_email", fake_send)
    service = InstitutionInvitationService(invitation_session)
    with pytest.raises(InvitationWorkflowError) as error:
        await service.invite("institution", "admin", "admin@example.test", "INSTITUTION_ADMIN")
    assert error.value.status_code == 422

    await service.invite("institution", "admin", "faculty@example.test", "MEMBER")
    with pytest.raises(InvitationWorkflowError) as mismatch:
        await service.accept("admin", delivered["token"])
    assert mismatch.value.status_code == 403
