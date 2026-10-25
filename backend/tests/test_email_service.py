from __future__ import annotations

from pydantic import SecretStr
import httpx
import pytest

import app.services.email as email_service
from app.services.email import EmailDeliveryError


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, url, *, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def response(status: int, body: dict):
    request = httpx.Request("POST", email_service._RESEND_ENDPOINT)
    return httpx.Response(status, json=body, request=request)


def configure(monkeypatch):
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", SecretStr("test-api-key"))
    monkeypatch.setattr(email_service.settings, "RESEND_FROM_EMAIL", "mail@example.test")
    monkeypatch.setattr(email_service.settings, "MAIL_FROM_NAME", "Kairos")
    monkeypatch.setattr(email_service.settings, "FRONTEND_URL", "https://kairos.example.test")


@pytest.mark.asyncio
async def test_transactional_email_includes_sender_html_and_text(monkeypatch):
    configure(monkeypatch)
    fake = FakeClient([response(200, {"id": "email-test-123"})])
    monkeypatch.setattr(email_service.httpx, "AsyncClient", lambda **_kwargs: fake)

    message_id = await email_service.send_transactional_email(
        to="recipient@example.test",
        subject="A test subject",
        html="<p>HTML version</p>",
        text="Plain text version",
        idempotency_key="test-operation-1",
    )

    assert message_id == "email-test-123"
    call = fake.calls[0]
    assert call["url"] == "https://api.resend.com/emails"
    assert call["json"]["from"] == "Kairos <mail@example.test>"
    assert call["json"]["to"] == ["recipient@example.test"]
    assert call["json"]["html"] == "<p>HTML version</p>"
    assert call["json"]["text"] == "Plain text version"
    assert call["headers"]["Idempotency-Key"] == "test-operation-1"
    assert "test-api-key" not in str(call["json"])


@pytest.mark.asyncio
async def test_transactional_email_retries_transient_provider_status(monkeypatch):
    configure(monkeypatch)
    fake = FakeClient([
        response(503, {"error": "temporary"}),
        response(200, {"id": "email-after-retry"}),
    ])
    monkeypatch.setattr(email_service.httpx, "AsyncClient", lambda **_kwargs: fake)

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(email_service.asyncio, "sleep", no_wait)
    message_id = await email_service.send_transactional_email(
        to="recipient@example.test", subject="Subject", html="<p>Hi</p>", text="Hi"
    )

    assert message_id == "email-after-retry"
    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_transactional_email_does_not_retry_permanent_provider_error(monkeypatch):
    configure(monkeypatch)
    fake = FakeClient([response(400, {"error": "invalid sender"})])
    monkeypatch.setattr(email_service.httpx, "AsyncClient", lambda **_kwargs: fake)

    with pytest.raises(EmailDeliveryError, match="permanently"):
        await email_service.send_transactional_email(
            to="recipient@example.test", subject="Subject", html="<p>Hi</p>", text="Hi"
        )

    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_missing_provider_configuration_fails_actionably(monkeypatch):
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", None)
    monkeypatch.setattr(email_service.settings, "RESEND_FROM_EMAIL", "")
    with pytest.raises(EmailDeliveryError, match="RESEND_API_KEY"):
        await email_service.send_transactional_email(
            to="recipient@example.test", subject="Subject", html="<p>Hi</p>", text="Hi"
        )


@pytest.mark.asyncio
async def test_verification_email_has_plain_text_and_expiry_guidance(monkeypatch):
    configure(monkeypatch)
    fake = FakeClient([response(200, {"id": "verify-id"})])
    monkeypatch.setattr(email_service.httpx, "AsyncClient", lambda **_kwargs: fake)

    await email_service.send_verification_email("student@example.test", "opaque-token")

    payload = fake.calls[0]["json"]
    assert payload["subject"] == "Verify your Kairos account"
    assert "30 minutes" in payload["html"]
    assert "30 minutes" in payload["text"]
    assert "https://kairos.example.test/verify-email?token=opaque-token" in payload["text"]

@pytest.mark.asyncio
async def test_progress_log_email_escapes_user_content_and_uses_idempotency(monkeypatch):
    configure(monkeypatch)
    fake = FakeClient([response(200, {"id": "progress-log-email-id"})])
    monkeypatch.setattr(email_service.httpx, "AsyncClient", lambda **_kwargs: fake)

    message_id = await email_service.send_work_log_notification(
        to="mentor@example.test",
        subject="[Kairos] Student Progress Update — Example Student — ERN-123",
        heading="Student Progress Update",
        fields={
            "Student": "Example Student",
            "Progress update": '<script>alert("x")</script>',
            "ERN / Enrollment Number": "ERN-123",
        },
        message="Completed a task & fixed a bug.",
        view_url="https://kairos.example.test/internships/during?log=log-123",
        idempotency_key="progress-log:log-123:faculty:account-123",
    )

    assert message_id == "progress-log-email-id"
    call = fake.calls[0]
    assert call["json"]["to"] == ["mentor@example.test"]
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in call["json"]["html"]
    assert "<script>" not in call["json"]["html"]
    assert "Completed a task &amp; fixed a bug." in call["json"]["html"]
    assert "Completed a task & fixed a bug." in call["json"]["text"]
    assert "View Progress Log" in call["json"]["html"]
    assert call["headers"]["Idempotency-Key"] == "progress-log:log-123:faculty:account-123"
