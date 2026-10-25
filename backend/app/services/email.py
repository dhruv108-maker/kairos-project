"""Centralized transactional email delivery for Kairos (Resend).

All application email workflows should call the public send_* helpers in this
module. Raw credentials, recipient message bodies, OTPs, and action tokens are
never written to logs.
"""
from __future__ import annotations

import asyncio
import logging
from html import escape
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_MAX_ATTEMPTS = 3
_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


class EmailDeliveryError(RuntimeError):
    """Raised when transactional email cannot be accepted by the provider."""


def _configured_sender() -> str:
    api_key = settings.RESEND_API_KEY
    if api_key is None or not api_key.get_secret_value().strip():
        raise EmailDeliveryError("Configure RESEND_API_KEY before sending email")
    address = (settings.RESEND_FROM_EMAIL or "").strip()
    if not address:
        raise EmailDeliveryError("Configure RESEND_FROM_EMAIL before sending email")
    # Resend accepts a display name in the From header. Avoid wrapping a value
    # that already contains a display name.
    if "<" in address and ">" in address:
        return address
    name = (settings.MAIL_FROM_NAME or "Kairos").strip() or "Kairos"
    return f"{name} <{address}>"


async def send_transactional_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
    idempotency_key: str | None = None,
) -> str:
    """Send a transactional message and return the provider's accepted message ID.

    Transient network failures and selected HTTP statuses are retried with
    bounded exponential backoff. Permanent 4xx responses are not retried.
    A successful return means accepted by Resend, not confirmed delivered.
    """
    sender = _configured_sender()
    api_key = settings.RESEND_API_KEY
    assert api_key is not None  # validated by _configured_sender
    payload: dict[str, Any] = {
        "from": sender,
        "to": [to],
        "subject": subject[:200],
        "html": html,
        "text": text,
    }
    headers = {"Authorization": f"Bearer {api_key.get_secret_value()}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await client.post(_RESEND_ENDPOINT, json=payload, headers=headers)
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                if response.is_error:
                    # Do not include provider body; it may contain recipient or request details.
                    raise EmailDeliveryError(
                        f"Email provider permanently rejected the message (HTTP {response.status_code})"
                    )
                try:
                    message_id = response.json().get("id")
                except (ValueError, AttributeError):
                    message_id = None
                if not isinstance(message_id, str) or not message_id:
                    raise EmailDeliveryError("Email provider accepted the request without a message ID")
                logger.info("Transactional email accepted by provider; provider_message_id=%s", message_id)
                return message_id
            except EmailDeliveryError:
                raise
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if status not in _RETRYABLE_STATUS_CODES:
                    raise EmailDeliveryError(
                        f"Email provider request failed permanently (HTTP {status})"
                    ) from None
                logger.warning(
                    "Transient email provider response; attempt=%s status=%s",
                    attempt,
                    status,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                logger.warning(
                    "Transient email provider transport failure; attempt=%s error_type=%s",
                    attempt,
                    type(exc).__name__,
                )
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(0.25 * (2 ** (attempt - 1)))

    raise EmailDeliveryError("Email provider did not accept the message after bounded retries") from last_error


async def send_verification_email(email: str, token: str) -> str:
    """Send a 30-minute single-use account verification link."""
    url = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={token}"
    safe_url = escape(url, quote=True)
    return await send_transactional_email(
        to=email,
        subject="Verify your Kairos account",
        html=(
            '<div style="font-family:Arial,sans-serif;line-height:1.6;color:#172033">'
            '<h1 style="font-size:22px">Welcome to Kairos</h1>'
            '<p>Verify your email address to finish setting up your Kairos account.</p>'
            f'<p><a href="{safe_url}">Verify email address</a></p>'
            '<p>This link expires in 30 minutes and can only be used once.</p>'
            '<p>If you did not create this account, you can ignore this message.</p>'
            '</div>'
        ),
        text=(
            "Welcome to Kairos. Verify your email address to finish setting up your account:\n"
            f"{url}\n\nThis link expires in 30 minutes and can only be used once. "
            "If you did not create this account, you can ignore this message."
        ),
    )


async def send_password_reset_email(email: str, token: str) -> str:
    """Send a 30-minute single-use password reset link."""
    url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    safe_url = escape(url, quote=True)
    return await send_transactional_email(
        to=email,
        subject="Reset your Kairos password",
        html=(
            '<div style="font-family:Arial,sans-serif;line-height:1.6;color:#172033">'
            '<h1 style="font-size:22px">Reset your password</h1>'
            '<p>A password reset was requested for your Kairos account.</p>'
            f'<p><a href="{safe_url}">Reset password</a></p>'
            '<p>This link expires in 30 minutes and can only be used once.</p>'
            '<p>If you did not request this change, ignore this email. Your password will remain unchanged.</p>'
            '</div>'
        ),
        text=(
            "A password reset was requested for your Kairos account. Use this single-use link "
            f"within 30 minutes:\n{url}\n\nIf you did not request this change, ignore this email. "
            "Your password will remain unchanged."
        ),
    )


async def send_workflow_notification(email: str, subject: str, message: str) -> str:
    """Send a plain-text business notification using the shared provider."""
    safe_message = escape(message)
    return await send_transactional_email(
        to=email,
        subject=subject,
        html=(
            '<div style="font-family:Arial,sans-serif;line-height:1.6;color:#172033">'
            '<p>This is a notification from Kairos.</p>'
            f"<p>{safe_message}</p>"
            '<p>If you have questions, contact your institution administrator.</p>'
            '</div>'
        ),
        text=f"This is a notification from Kairos.\n\n{message}\n\nContact your institution administrator if you have questions.",
    )


async def send_institution_invitation_email(
    email: str, institution_name: str, role: str, token: str
) -> str:
    """Deliver a seven-day, single-use institutional invitation."""
    url = f"{settings.FRONTEND_URL.rstrip('/')}/institution-invite?token={token}"
    safe_url = escape(url, quote=True)
    safe_institution = escape(institution_name)
    safe_role = escape(role)
    return await send_transactional_email(
        to=email,
        subject=f"Invitation to join {institution_name} on Kairos",
        html=(
            '<div style="font-family:Arial,sans-serif;line-height:1.6;color:#172033">'
            '<h1 style="font-size:22px">You are invited to Kairos</h1>'
            f"<p>You have been invited to join {safe_institution} as {safe_role}.</p>"
            '<p>Sign in to your verified Kairos account and accept the invitation.</p>'
            f'<p><a href="{safe_url}">Accept invitation</a></p>'
            '<p>This link expires in seven days and can only be used once.</p>'
            '<p>If you were not expecting this invitation, you can ignore this message.</p>'
            '</div>'
        ),
        text=(
            f"You have been invited to join {institution_name} on Kairos as {role}.\n"
            f"Accept the invitation: {url}\n\n"
            "This link expires in seven days and can only be used once. "
            "If you were not expecting this invitation, you can ignore this message."
        ),
    )

async def send_work_log_notification(
    *,
    to: str,
    subject: str,
    heading: str,
    fields: dict[str, str],
    message: str,
    view_url: str,
    idempotency_key: str,
) -> str:
    """Send an escaped progress-log or mentor-feedback email through Resend."""
    safe_heading = escape(heading)
    safe_message = escape(message)
    safe_url = escape(view_url, quote=True)
    safe_rows = "".join(
        f"<tr><th align=\"left\" style=\"padding:6px 12px 6px 0;vertical-align:top\">{escape(str(label))}</th>"
        f"<td style=\"padding:6px 0;white-space:pre-wrap\">{escape(str(value))}</td></tr>"
        for label, value in fields.items() if value
    )
    html = (
        '<div style="font-family:Arial,sans-serif;line-height:1.6;color:#172033;max-width:720px">'
        f"<h1 style=\"font-size:22px\">{safe_heading}</h1>"
        f"<table style=\"border-collapse:collapse\">{safe_rows}</table>"
        f"<p style=\"white-space:pre-wrap\">{safe_message}</p>"
        f'<p><a href="{safe_url}" style="display:inline-block;padding:10px 16px;background:#0f766e;color:#fff;text-decoration:none;border-radius:6px">View Progress Log</a></p>'
        '<p style="font-size:12px;color:#64748b">Sign in to Kairos to view the complete record and respond. This notification contains no sign-in token.</p>'
        "</div>"
    )
    text_fields = "\n".join(f"{label}: {value}" for label, value in fields.items() if value)
    text = f"{heading}\n\n{text_fields}\n\n{message}\n\nView Progress Log: {view_url}\n\nSign in to Kairos to view the complete record and respond."
    return await send_transactional_email(
        to=to, subject=subject, html=html, text=text, idempotency_key=idempotency_key,
    )
