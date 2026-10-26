from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db_session
from app.core.security import create_token, hash_password
from app.main import app
from app.models import Base
from app.models.academic import Account


@pytest_asyncio.fixture
async def identity_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session.add(
            Account(
                id="account-a",
                email="identity@example.com",
                password_hash=hash_password("test password that is long enough"),
                full_name="Identity Test",
                is_active=True,
                is_verified=True,
                token_version=0,
            )
        )
        await session.commit()

    async def override_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    token = create_token("account-a", "access", timedelta(minutes=5), token_version=0)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, {"Authorization": f"Bearer {token}"}

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_identity_status_requires_authentication_and_uses_token_account(identity_client):
    client, headers = identity_client

    unauthenticated = await client.get("/api/v1/identity-verification/status")
    assert unauthenticated.status_code == 401

    response = await client.get("/api/v1/identity-verification/status", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "not_started"
    assert response.json()["verified"] is False
    assert response.json()["identity_verified"] is False
    assert response.json()["email_verified"] is True
    assert response.json()["identity_verification_status"] == "not_started"
    assert response.json()["available"] is False


@pytest.mark.asyncio
async def test_identity_initiation_requires_consent_and_fails_safely_when_unavailable(identity_client):
    client, headers = identity_client

    no_consent = await client.post(
        "/api/v1/identity-verification/initiate",
        headers=headers,
        json={"aadhaar_number": "123456789012", "consent": False, "consent_notice_version": "notice-v1"},
    )
    assert no_consent.status_code == 422

    unavailable = await client.post(
        "/api/v1/identity-verification/initiate",
        headers=headers,
        json={"aadhaar_number": "123456789012", "consent": True, "consent_notice_version": " notice-v1 "},
    )
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["code"] == "identity_verification_unavailable"
    assert "Retry-After" in unavailable.headers


@pytest.mark.asyncio
async def test_identity_initiation_rejects_client_supplied_identity_or_verified_fields(identity_client):
    client, headers = identity_client

    response = await client.post(
        "/api/v1/identity-verification/initiate",
        headers=headers,
        json={
            "aadhaar_number": "123456789012",
            "consent": True,
            "consent_notice_version": "notice-v1",
            "user_id": "another-account",
            "verified": True,
        },
    )
    assert response.status_code == 422



@pytest.mark.asyncio
async def test_optional_identity_details_require_consent_and_never_verify_account(identity_client):
    client, headers = identity_client
    no_consent = await client.put(
        "/api/v1/identity-verification/details",
        headers=headers,
        json={"declared_name": "  Example Student ", "consent": False, "consent_notice_version": "notice-v1"},
    )
    assert no_consent.status_code == 422

    saved = await client.put(
        "/api/v1/identity-verification/details",
        headers=headers,
        json={"declared_name": "  Example Student ", "consent": True, "consent_notice_version": " notice-v1 "},
    )
    assert saved.status_code == 200
    assert saved.json()["declared_name"] == "Example Student"

    status = await client.get("/api/v1/identity-verification/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["declared_name"] == "Example Student"
    assert status.json()["verified"] is False
    assert status.json()["identity_verified"] is False
    assert status.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_optional_identity_details_reject_forged_verification_fields(identity_client):
    client, headers = identity_client
    response = await client.put(
        "/api/v1/identity-verification/details",
        headers=headers,
        json={"declared_name": "Example Student", "consent": True, "consent_notice_version": "notice-v1",
              "verified": True, "identity_verified": True, "account_id": "another-account"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_optional_identity_details_require_authentication(identity_client):
    client, _ = identity_client
    response = await client.put(
        "/api/v1/identity-verification/details",
        json={"declared_name": "Example Student", "consent": True, "consent_notice_version": "notice-v1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_identity_status_cannot_be_switched_to_another_account_by_client_input(identity_client):
    client, headers = identity_client
    response = await client.get(
        "/api/v1/identity-verification/status",
        headers=headers,
        params={"account_id": "another-account", "user_id": "another-account"},
    )
    assert response.status_code == 200
    # The endpoint derives identity solely from CurrentAccount/token claims; client
    # identifiers are not accepted as authority to read another account's record.
    assert response.json()["status"] == "not_started"
    assert response.json()["email_verified"] is True
    assert response.json()["identity_verified"] is False
