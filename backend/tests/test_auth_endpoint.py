import pytest
from fastapi import HTTPException, Response

from app.api import auth
from app.api.schemas import LoginRequest
from app.models.academic import Account


class FakeSession:
    def add(self, record) -> None:
        self.added = record

    async def commit(self) -> None:
        return None


class FakeIdentityService:
    def __init__(self, session, account):
        self.account = account
        self.requested_email = None

    async def get_account_by_email(self, email: str):
        self.requested_email = email
        return self.account


@pytest.mark.asyncio
async def test_login_looks_up_normalized_email_and_returns_frontend_contract(monkeypatch):
    account = Account(
        id="test-account-id",
        email="student@example.test",
        password_hash="hashed-test-password",
        full_name="Student Example",
        is_active=True,
        is_verified=True,
        token_version=0,
    )
    service = FakeIdentityService(None, account)
    monkeypatch.setattr(auth, "IdentityService", lambda session: service)
    monkeypatch.setattr(auth, "verify_password", lambda password, encoded: password == "correct-password")
    monkeypatch.setattr(auth, "create_token", lambda *args, **kwargs: "test-access-token")

    async def roles_for_account(db, account_id):
        assert account_id == account.id
        return ["STUDENT"]

    monkeypatch.setattr(auth, "account_roles", roles_for_account)
    response = await auth.login(
        LoginRequest(email=" STUDENT@Example.test ", password="correct-password"),
        FakeSession(), Response(),
    )

    assert service.requested_email == "student@example.test"
    assert response.access_token == "test-access-token"
    assert response.token_type == "bearer"
    assert response.account.full_name == "Student Example"
    assert response.account.roles == ["STUDENT"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "account,password",
    [
        (None, "correct-password"),
        (
            Account(
                id="test-account-id",
                email="student@example.test",
                password_hash="hashed-test-password",
                full_name="Student Example",
                is_active=True,
                is_verified=True,
                token_version=0,
            ),
            "wrong-password",
        ),
    ],
)
async def test_login_rejects_missing_account_or_invalid_password(monkeypatch, account, password):
    monkeypatch.setattr(auth, "IdentityService", lambda session: FakeIdentityService(session, account))
    monkeypatch.setattr(auth, "verify_password", lambda supplied, encoded: supplied == "correct-password")

    with pytest.raises(HTTPException) as exc:
        await auth.login(LoginRequest(email="student@example.test", password=password), FakeSession())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"
