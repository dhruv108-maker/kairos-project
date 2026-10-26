from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.academic import Account
from app.models.identity_verification import IdentityVerification
from app.modules.identity_verification.provider import IdentityProviderUnavailable
from app.modules.identity_verification.service import IdentityVerificationService


@pytest_asyncio.fixture
async def identity_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        account = Account(
            id="separation-account", email="separation@example.test",
            password_hash="hash", full_name="Test Account",
            is_active=True, is_verified=True, identity_verified=False,
            token_version=0,
        )
        db.add(account)
        await db.commit()
        yield db, account
    await engine.dispose()


def make_attempt(account_id, status="pending"):
    return IdentityVerification(
        id=str(uuid4()), account_id=account_id, provider="test-provider",
        provider_reference=f"ref-{uuid4()}", status=status,
        consented_at=datetime.now(UTC).replace(tzinfo=None),
        consent_notice_version="test-v1",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )


@pytest.mark.asyncio
async def test_identity_summary_defaults_false_and_email_flag_is_independent(identity_db):
    db, account = identity_db
    await db.refresh(account)
    assert account.is_verified is True
    assert account.identity_verified is False


@pytest.mark.asyncio
async def test_declared_details_and_nonverified_lifecycle_never_verify_identity(identity_db):
    db, account = identity_db
    service = IdentityVerificationService(db)
    await service.save_details(
        str(account.id), "User Declared", True, "notice-v1",
    )
    for lifecycle in ("pending", "failed", "expired", "cancelled", "review_required"):
        db.add(make_attempt(account.id, lifecycle))
        await db.commit()
        result = await service.status(account.id)
        await db.refresh(account)
        assert result["identity_verified"] is False
        assert account.identity_verified is False
        assert account.is_verified is True


@pytest.mark.asyncio
async def test_ocr_only_provider_cannot_set_identity_summary(identity_db):
    db, account = identity_db
    record = make_attempt(account.id, "pending")
    db.add(record)
    await db.commit()
    service = IdentityVerificationService(db)
    with pytest.raises(IdentityProviderUnavailable):
        await service.apply_authoritative_result(
            account_id=account.id,
            provider_reference=record.provider_reference,
            payload={"verified": True, "ocr_success": True},
        )
    await db.refresh(account)
    await db.refresh(record)
    assert account.identity_verified is False
    assert account.is_verified is True
    assert record.status == "pending"


@pytest.mark.asyncio
async def test_only_provider_validated_authoritative_result_updates_identity_atomically(identity_db):
    db, account = identity_db

    class TrustedTestProvider:
        async def initiate(self, **kwargs):
            raise AssertionError("not used")
        async def validate_result(self, *, provider_reference, payload):
            return payload.get("trusted_test_validation") is True

    record = make_attempt(account.id, "pending")
    db.add(record)
    await db.commit()
    service = IdentityVerificationService(db, provider=TrustedTestProvider())
    result = await service.apply_authoritative_result(
        account_id=account.id,
        provider_reference=record.provider_reference,
        payload={"trusted_test_validation": True},
    )
    await db.refresh(account)
    await db.refresh(record)
    assert result["identity_verified"] is True
    assert account.identity_verified is True
    assert account.is_verified is True
    assert record.status == "verified"
    assert record.completed_at is not None


@pytest.mark.asyncio
async def test_legacy_verified_record_without_summary_is_not_trusted(identity_db):
    db, account = identity_db
    db.add(make_attempt(account.id, "verified"))
    await db.commit()
    result = await IdentityVerificationService(db).status(account.id)
    await db.refresh(account)
    assert result["status"] == "review_required"
    assert result["verified"] is False
    assert result["identity_verified"] is False
    assert account.identity_verified is False
    assert account.is_verified is True
