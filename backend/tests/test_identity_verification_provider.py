import asyncio

import pytest

from app.modules.identity_verification.provider import (
    IdentityProviderUnavailable,
    SignzyAadhaarProvider,
    VerificationStart,
)
from app.modules.identity_verification.service import IdentityVerificationService
from app.models.academic import Account


class FakeDatabase:
    def __init__(self, latest=None):
        self.latest = latest
        self.account = Account(
            id="account-a", email="a@example.test", password_hash="x",
            full_name="A", is_verified=True, identity_verified=False, is_active=True,
        )
        self.added = []
        self.commits = 0
        self.refreshed = []

    async def scalar(self, statement):
        if "accounts" in str(statement):
            return self.account
        if "identity_details" in str(statement):
            return None
        return self.latest

    def add(self, record):
        self.added.append(record)

    async def commit(self):
        self.commits += 1

    async def refresh(self, record):
        self.refreshed.append(record)


def test_signzy_adapter_fails_closed_when_disabled_or_unconfigured():
    async def run():
        with pytest.raises(IdentityProviderUnavailable):
            await SignzyAadhaarProvider().initiate(
                account_id="account-test",
                consent_notice_version="test-v1",
                aadhaar_number="123456789012",
            )

    asyncio.run(run())


def test_status_for_new_account_reflects_provider_configuration():
    async def run():
        result = await IdentityVerificationService(FakeDatabase()).status("account-a")
        assert result["status"] == "not_started"
        assert result["verified"] is False
        assert result["available"] is False
        assert result["provider"] == "signzy"

    asyncio.run(run())


def test_explicit_consent_is_required_before_provider_is_called():
    class Provider:
        name = "test"
        is_available = True

        async def initiate(self, **kwargs):
            raise AssertionError("Provider must not be called without consent")

    async def run():
        db = FakeDatabase()
        service = IdentityVerificationService(db, provider=Provider())
        with pytest.raises(ValueError, match="Explicit consent"):
            await service.initiate("account-a", False, "notice-v1", "123456789012")
        assert db.added == []
        assert db.commits == 0

    asyncio.run(run())


def test_authoritative_provider_success_sets_identity_flag_without_persisting_aadhaar():
    class Provider:
        name = "test-provider"
        is_available = True

        async def initiate(self, *, account_id, consent_notice_version, aadhaar_number):
            assert account_id == "account-a"
            assert consent_notice_version == "notice-v1"
            assert aadhaar_number == "123456789012"
            return VerificationStart("transaction-123", None, verified=True)

    async def run():
        db = FakeDatabase()
        service = IdentityVerificationService(db, provider=Provider())
        result = await service.initiate("account-a", True, " notice-v1 ", "123456789012")
        assert result["status"] == "verified"
        assert result["identity_verified"] is True
        assert result["email_verified"] is True
        assert db.account.identity_verified is True
        assert db.added[0].provider_reference == "transaction-123"
        assert not hasattr(db.added[0], "aadhaar_number")
        assert db.commits == 1

    asyncio.run(run())


def test_negative_provider_result_never_marks_account_verified():
    class Provider:
        name = "test-provider"
        is_available = True

        async def initiate(self, **kwargs):
            return VerificationStart("transaction-456", None, verified=False)

    async def run():
        db = FakeDatabase()
        service = IdentityVerificationService(db, provider=Provider())
        result = await service.initiate("account-a", True, "notice-v1", "123456789012")
        assert result["status"] == "failed"
        assert result["identity_verified"] is False
        assert db.account.identity_verified is False
        assert db.added[0].status == "failed"

    asyncio.run(run())


def test_invalid_aadhaar_number_is_rejected_before_provider_call():
    class Provider:
        name = "test-provider"
        is_available = True

        async def initiate(self, **kwargs):
            raise AssertionError("Provider must not be called for malformed Aadhaar")

    async def run():
        db = FakeDatabase()
        service = IdentityVerificationService(db, provider=Provider())
        with pytest.raises(ValueError, match="12-digit"):
            await service.initiate("account-a", True, "notice-v1", "1234")
        assert db.added == []
        assert db.commits == 0

    asyncio.run(run())
