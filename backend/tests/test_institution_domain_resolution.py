import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.schemas import FacultyRegistration, StudentRegistration
from app.models import Account, Base, Institution, InstitutionDomain
from app.modules.institutions.router import public_institutions, resolve_institution_domain


@pytest_asyncio.fixture
async def domain_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        account = Account(id="domain-admin", email="admin@example.test", password_hash="x", full_name="Admin", is_active=True, is_verified=True)
        institution = Institution(id="institution-gsfc", name="GSFC University", slug="gsfc-university", status="ACTIVE", created_by_account_id=account.id)
        session.add_all([account, institution])
        await session.flush()
        session.add_all([
            InstitutionDomain(id="domain-gsfc", institution_id=institution.id, normalized_domain="gsfcuniversity.ac.in", is_verified=True),
            InstitutionDomain(id="domain-gsfc-alt", institution_id=institution.id, normalized_domain="mail.gsfcuniversity.ac.in", is_verified=True),
            InstitutionDomain(id="domain-unverified", institution_id=institution.id, normalized_domain="unverified.example.test", is_verified=False),
        ])
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_resolves_registered_domain_case_and_trailing_dot(domain_session):
    result = await resolve_institution_domain(domain_session, " GSFCUNIVERSITY.AC.IN. ")
    assert result == {"status": "matched", "institution": {"id": "institution-gsfc", "name": "GSFC University"}}


@pytest.mark.asyncio
async def test_supports_multiple_verified_domains_for_one_institution(domain_session):
    result = await resolve_institution_domain(domain_session, "mail.gsfcuniversity.ac.in")
    assert result["status"] == "matched"
    assert result["institution"]["name"] == "GSFC University"


@pytest.mark.asyncio
async def test_unknown_and_unverified_domains_do_not_match(domain_session):
    assert (await resolve_institution_domain(domain_session, "unknown.example.test"))["status"] == "not_found"
    assert (await resolve_institution_domain(domain_session, "gsfcuniversity.ac.in.attacker.test"))["status"] == "not_found"
    assert (await resolve_institution_domain(domain_session, "unverified.example.test"))["status"] == "not_found"


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ["@bad", "bad domain.com", "-bad.com", "bad..com", "localhost"])
async def test_malformed_domain_is_rejected(domain_session, domain):
    with pytest.raises(HTTPException) as exc:
        await resolve_institution_domain(domain_session, domain)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_public_directory_returns_names_and_database_ids(domain_session):
    result = await public_institutions(domain_session, "GSFC")
    assert result["items"] == [{"id": "institution-gsfc", "name": "GSFC University"}]


def test_student_registration_contract_preserves_cohort_and_institution_ids():
    payload = StudentRegistration(email=" Student@Example.test ", password="very-secure-test-password", full_name=" Student ", institution_id="institution-gsfc", enrollment_number=" ENR-001 ", cohort_id="cohort-001")
    assert payload.email == "student@example.test"
    assert payload.full_name == "Student"
    assert payload.enrollment_number == "ENR-001"
    assert payload.cohort_id == "cohort-001"
    assert payload.institution_id == "institution-gsfc"


def test_faculty_registration_contract_keeps_department_and_institution():
    payload = FacultyRegistration(email="faculty@example.test", password="very-secure-test-password", full_name="Faculty", institution_id="institution-gsfc", employee_code="EMP-1", department_id="department-1", designation="Professor")
    assert payload.institution_id == "institution-gsfc"
    assert payload.department_id == "department-1"

@pytest.mark.asyncio
async def test_ambiguous_domain_match_returns_fallback_without_exposing_ids():
    class AmbiguousResult:
        def all(self):
            return [("institution-one", "Institution One"), ("institution-two", "Institution Two")]
    class AmbiguousSession:
        async def execute(self, statement):
            return AmbiguousResult()
    result = await resolve_institution_domain(AmbiguousSession(), "ambiguous.example.test")
    assert result == {"status": "ambiguous", "institution": None}
