import asyncio

import pytest

from app.modules.identity_verification.provider import (
    IdentityProviderUnavailable,
    VerificationStart,
    VerificoAadhaarProvider,
)
from app.modules.identity_verification.service import IdentityVerificationService


class FakeDatabase:
    def __init__(self, latest=None):
        self.latest = latest
        self.added = []
        self.commits = 0
        self.refreshed = []

    async def scalar(self, statement):
        return self.latest

    def add(self, record):
        self.added.append(record)

    async def commit(self):
        self.commits += 1

    async def refresh(self, record):
        self.refreshed.append(record)


def test_verifico_adapter_fails_closed_when_only_aadhaar_ocr_is_documented():
    async def run():
        with pytest.raises(IdentityProviderUnavailable):
            await VerificoAadhaarProvider().initiate(
                account_id="account-test", consent_notice_version="test-v1"
            )

    asyncio.run(run())


def test_status_for_new_account_is_explicitly_unavailable():
    async def run():
        result = await IdentityVerificationService(FakeDatabase()).status("account-a")
        assert result["status"] == "not_started"
        assert result["verified"] is False
        assert result["available"] is False
        assert result["provider"] == "verifico"

    asyncio.run(run())


def test_unsupported_provider_does_not_create_a_fake_pending_record():
    async def run():
        db = FakeDatabase()
        service = IdentityVerificationService(db, provider=VerificoAadhaarProvider())
        with pytest.raises(IdentityProviderUnavailable):
            await service.initiate("account-a", True, "notice-v1")
        assert db.added == []
        assert db.commits == 0

    asyncio.run(run())


def test_explicit_consent_is_required_before_provider_is_called():
    class Provider:
        async def initiate(self, **kwargs):
            raise AssertionError("Provider must not be called without consent")

    async def run():
        db = FakeDatabase()
        service = IdentityVerificationService(db, provider=Provider())
        with pytest.raises(ValueError, match="Explicit consent"):
            await service.initiate("account-a", False, "notice-v1")
        assert db.added == []
        assert db.commits == 0

    asyncio.run(run())


def test_consent_notice_version_is_trimmed_before_provider_and_storage():
    class Provider:
        async def initiate(self, *, account_id, consent_notice_version):
            assert account_id == "account-a"
            assert consent_notice_version == "notice-v1"
            return VerificationStart("transaction-123", None)

    async def run():
        db = FakeDatabase()
        service = IdentityVerificationService(db, provider=Provider())
        result = await service.initiate("account-a", True, "  notice-v1  ")
        assert result["status"] == "pending"
        assert db.added[0].consent_notice_version == "notice-v1"
        assert db.added[0].account_id == "account-a"
        assert db.commits == 1

    asyncio.run(run())


def test_invalid_provider_reference_does_not_create_record():
    class Provider:
        async def initiate(self, **kwargs):
            return VerificationStart("  ", None)

    async def run():
        db = FakeDatabase()
        with pytest.raises(IdentityProviderUnavailable):
            await IdentityVerificationService(db, provider=Provider()).initiate(
                "account-a", True, "notice-v1"
            )
        assert db.added == []
        assert db.commits == 0

    asyncio.run(run())


def test_non_https_provider_redirect_is_rejected():
    class Provider:
        async def initiate(self, **kwargs):
            return VerificationStart("transaction-123", "http://unsafe.example/verify")

    async def run():
        db = FakeDatabase()
        with pytest.raises(IdentityProviderUnavailable):
            await IdentityVerificationService(db, provider=Provider()).initiate(
                "account-a", True, "notice-v1"
            )
        assert db.added == []
        assert db.commits == 0

    asyncio.run(run())


def test_provider_timeout_fails_closed_without_creating_attempt():
    class Provider:
        async def initiate(self, **kwargs):
            raise TimeoutError()

    async def run():
        db = FakeDatabase()
        with pytest.raises(IdentityProviderUnavailable):
            await IdentityVerificationService(db, provider=Provider()).initiate(
                "account-a", True, "notice-v1"
            )
        assert db.added == []
        assert db.commits == 0

    asyncio.run(run())


def test_client_cannot_turn_ocr_or_payload_into_verified_status():
    async def run():
        with pytest.raises(IdentityProviderUnavailable):
            await VerificoAadhaarProvider().validate_result(
                provider_reference="provider-ref-test",
                payload={"verified": True, "status": "verified"},
            )

    asyncio.run(run())
