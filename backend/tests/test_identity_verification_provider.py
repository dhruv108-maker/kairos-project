import asyncio

import pytest

from app.core.config import settings
from app.modules.identity_verification.provider import (
    IdentityProviderUnavailable,
    VerificoAadhaarOcrProvider,
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


def test_verifico_adapter_unavailable_without_private_api_key(monkeypatch):
    monkeypatch.setattr(settings, "VERIFICO_API", None)
    assert VerificoAadhaarOcrProvider().is_available is False


def test_status_reports_ocr_separately_from_identity_verification(monkeypatch):
    async def run():
        monkeypatch.setattr(settings, "VERIFICO_API", None)
        result = await IdentityVerificationService(FakeDatabase()).status("account-a")
        assert result["status"] == "not_started"
        assert result["verified"] is False
        assert result["identity_verified"] is False
        assert result["available"] is False
        assert result["ocr_available"] is False
        assert result["provider"] == "verifico_ocr"

    asyncio.run(run())


def test_ocr_provider_never_claims_identity_verification():
    async def run():
        provider = VerificoAadhaarOcrProvider()
        with pytest.raises(IdentityProviderUnavailable, match="does not verify"):
            await provider.initiate(
                account_id="account-a",
                consent_notice_version="test-v1",
                aadhaar_number="123456789012",
            )
        with pytest.raises(IdentityProviderUnavailable, match="not an authoritative"):
            await provider.validate_result(provider_reference="fake-ref", payload={"verified": True})

    asyncio.run(run())


def test_identity_service_does_not_turn_ocr_into_verified_status():
    class Provider:
        name = "verifico_ocr"
        is_available = True

        async def initiate(self, **kwargs):
            return type("OCRResult", (), {"provider_reference": "ocr-1", "verified": True})()

    async def run():
        db = FakeDatabase()
        service = IdentityVerificationService(db, provider=Provider())
        with pytest.raises(IdentityProviderUnavailable):
            await service.initiate("account-a", True, "notice-v1", "123456789012")
        assert db.account.identity_verified is False
        assert db.added == []
        assert db.commits == 0

    asyncio.run(run())


def test_aadhaar_ocr_result_projection_masks_full_number(monkeypatch):
    # The provider adapter's allowlist helper never exposes the full number.
    provider = VerificoAadhaarOcrProvider()
    fields = {
        "aadhaar_number": "1234 5678 9012",
        "name": "Example Person",
        "address": "Example Road",
        "photo": "base64-sensitive-value",
    }
    aadhaar = provider._first_text(fields, "aadhaar_number")
    digits = "".join(char for char in (aadhaar or "") if char.isdigit())
    projection = {
        "name": provider._first_text(fields, "name", "full_name"),
        "aadhaar_last4": digits[-4:] if len(digits) >= 4 else None,
    }
    assert projection == {"name": "Example Person", "aadhaar_last4": "9012"}
    assert "aadhaar_number" not in projection
    assert "photo" not in projection


def test_settings_load_lowercase_verifico_api_from_root_env_file(tmp_path):
    from app.core.config import Settings

    env_file = tmp_path / ".env"
    env_file.write_text(
        "verifico_api=ocr_live_test_only\n"
        "DB_HOST=localhost\n"
        "DB_USER=test-user\n"
        "DB_PASSWORD=test-password\n"
        "JWT_SECRET_KEY=test-secret-that-is-long-enough\n",
        encoding="utf-8",
    )
    loaded = Settings(_env_file=env_file)
    assert loaded.VERIFICO_API is not None
    assert loaded.VERIFICO_API.get_secret_value() == "ocr_live_test_only"


def test_local_env_file_overrides_root_env_file(tmp_path):
    from app.core.config import Settings

    root_env = tmp_path / ".env"
    local_env = tmp_path / ".env.local"
    required = (
        "DB_HOST=localhost\n"
        "DB_USER=test-user\n"
        "DB_PASSWORD=test-password\n"
        "JWT_SECRET_KEY=test-secret-that-is-long-enough\n"
    )
    root_env.write_text(required + "verifico_api=ocr_live_from_root\n", encoding="utf-8")
    local_env.write_text("verifico_api=ocr_live_local_override\n", encoding="utf-8")
    loaded = Settings(_env_file=(root_env, local_env))
    assert loaded.VERIFICO_API is not None
    assert loaded.VERIFICO_API.get_secret_value() == "ocr_live_local_override"
