from __future__ import annotations

import httpx

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    pass


async def send_verification_email(email: str, token: str) -> None:
    """Send a verification link through Resend; never log or persist the raw token."""
    api_key = settings.RESEND_API_KEY
    from_email = settings.RESEND_FROM_EMAIL
    if api_key is None or not api_key.get_secret_value() or not from_email:
        raise EmailDeliveryError("Resend API key and RESEND_FROM_EMAIL must be configured")

    link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={token}"
    payload = {
        "from": from_email,
        "to": [email],
        "subject": "Verify your Kairos account",
        "html": (
            "<p>Verify your Kairos account using the link below. "
            "This link expires in 30 minutes.</p>"
            f'<p><a href="{link}">Verify email</a></p>'
        ),
    }
    headers = {"Authorization": f"Bearer {api_key.get_secret_value()}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.resend.com/emails", json=payload, headers=headers
        )
        response.raise_for_status()


async def send_password_reset_email(email: str, token: str) -> None:
    """Send a single-use password reset link without logging the token."""
    api_key = settings.RESEND_API_KEY
    from_email = settings.RESEND_FROM_EMAIL
    if api_key is None or not api_key.get_secret_value() or not from_email:
        raise EmailDeliveryError("Resend API key and RESEND_FROM_EMAIL must be configured")
    link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    payload = {
        "from": from_email,
        "to": [email],
        "subject": "Reset your Kairos password",
        "html": (
            "<p>A password reset was requested for your Kairos account. "
            "If you did not request this, you can ignore this email. "
            "This link expires in 30 minutes.</p>"
            f'<p><a href="{link}">Reset password</a></p>'
        ),
    }
    headers = {"Authorization": f"Bearer {api_key.get_secret_value()}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
        response.raise_for_status()


async def send_workflow_notification(email: str, subject: str, message: str) -> None:
    """Send a generic workflow notification after the business transaction commits."""
    from html import escape

    api_key = settings.RESEND_API_KEY
    from_email = settings.RESEND_FROM_EMAIL
    if api_key is None or not api_key.get_secret_value() or not from_email:
        raise EmailDeliveryError("Resend API key and RESEND_FROM_EMAIL must be configured")
    payload = {
        "from": from_email,
        "to": [email],
        "subject": subject[:200],
        "html": f"<p>{escape(message)}</p>",
    }
    headers = {"Authorization": f"Bearer {api_key.get_secret_value()}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
        response.raise_for_status()


async def send_institution_invitation_email(email: str, institution_name: str, role: str, token: str) -> None:
    """Deliver an invitation token; the raw token is never persisted."""
    from html import escape

    api_key = settings.RESEND_API_KEY
    from_email = settings.RESEND_FROM_EMAIL
    if api_key is None or not api_key.get_secret_value() or not from_email:
        raise EmailDeliveryError("Resend API key and RESEND_FROM_EMAIL must be configured")
    link = f"{settings.FRONTEND_URL.rstrip('/')}/institution-invite?token={token}"
    payload = {
        "from": from_email,
        "to": [email],
        "subject": f"Invitation to join {institution_name} on Kairos",
        "html": (
            f"<p>You have been invited to join {escape(institution_name)} on Kairos as {escape(role)}.</p>"
            "<p>Sign in to your verified Kairos account and accept the invitation using this link. "
            "The link expires in seven days and can only be used once.</p>"
            f'<p><a href="{link}">Accept institution invitation</a></p>'
        ),
    }
    headers = {"Authorization": f"Bearer {api_key.get_secret_value()}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
        response.raise_for_status()
