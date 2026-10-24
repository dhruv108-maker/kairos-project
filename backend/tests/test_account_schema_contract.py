from sqlalchemy import select
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import configure_mappers

from app.api.schemas import AuthResponse, LoginRequest, StudentRegistration
from app.models.academic import Account
from app.modules.identity.service import IdentityService


def test_account_model_declares_required_full_name_column():
    column = Account.__table__.c.full_name
    assert column.type.length == 255
    assert column.nullable is False


def test_email_lookup_selects_the_account_name_column():
    statement = select(Account).where(Account.email == "student@example.test")
    compiled = str(statement.compile(dialect=mysql.dialect()))
    assert "accounts.full_name" in compiled


def test_identity_service_uses_account_email_field():
    statement = select(Account).where(Account.email == "student@example.test")
    compiled = str(statement.compile(dialect=mysql.dialect()))
    assert "accounts.email" in compiled
    assert "accounts.full_name" in compiled


def test_login_and_registration_contracts_normalize_email_and_name():
    login = LoginRequest(email="  STUDENT@Example.test ", password="long-enough-password")
    assert login.email == "student@example.test"

    registration = StudentRegistration(
        email=" STUDENT@Example.test ",
        password="long-enough-password-123",
        full_name="  Student Example  ",
        enrollment_number="ENR-TEST-01",
        cohort_id="cohort-test",
    )
    assert registration.email == "student@example.test"
    assert registration.full_name == "Student Example"


def test_auth_response_keeps_frontend_contract_fields():
    assert set(AuthResponse.model_fields) == {"access_token", "token_type", "expires_in", "account"}
    assert set(Account.__table__.columns.keys()) >= {
        "id", "email", "password_hash", "full_name", "is_active", "is_verified", "token_version"
    }
