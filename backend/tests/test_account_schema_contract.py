import importlib.util
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects import mysql

from app.api.schemas import AuthResponse, LoginRequest, StudentRegistration
from app.models.academic import Account


def test_account_model_declares_required_full_name_column():
    column = Account.__table__.c.full_name
    assert column.type.length == 255
    assert column.nullable is False


def test_migration_backfills_existing_display_name_before_email_fallback(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20261024_17_account_full_name.py"
    )
    spec = importlib.util.spec_from_file_location("account_full_name_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    statements = []
    monkeypatch.setattr(migration.op, "execute", statements.append)
    migration._backfill_full_name({"id", "email", "display_name", "full_name"})

    sql = str(statements[0])
    assert "display_name" in sql
    assert sql.index("display_name") < sql.index("SUBSTRING_INDEX(email")
    assert "UPDATE accounts SET full_name" in sql
    assert "WHERE full_name IS NULL OR TRIM(full_name) = ''" in sql


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
