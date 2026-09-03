"""Email delivery for invites (console or SMTP)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _smtp_configured() -> bool:
    return bool(getattr(settings, "smtp_host", None) and getattr(settings, "smtp_from", None))


async def send_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> dict[str, Any]:
    if not _smtp_configured():
        logger.info("email_console", to=to, subject=subject, body=text_body[:500])
        return {"ok": True, "provider": "console", "to": to}

    host = settings.smtp_host
    port = int(getattr(settings, "smtp_port", None) or 587)
    user = getattr(settings, "smtp_user", None)
    password = getattr(settings, "smtp_password", None)
    mail_from = settings.smtp_from
    use_tls = getattr(settings, "smtp_tls", True)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if use_tls:
                smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        logger.info("email_sent", to=to, subject=subject, provider="smtp")
        return {"ok": True, "provider": "smtp", "to": to}
    except Exception as e:
        logger.error("email_send_failed", error=str(e), to=to)
        return {"ok": False, "error": str(e)}


async def send_invite_email(
    *,
    to: str,
    org_name: str,
    role: str,
    token: str,
    inviter_name: str | None = None,
) -> dict[str, Any]:
    frontend = getattr(settings, "frontend_url", None) or "http://localhost:3000"
    link = f"{frontend}/invite?token={token}"
    subject = f"You're invited to {org_name} on AURI.AI"
    text = (
        f"You have been invited to join {org_name} as {role}.\n\n"
        f"Accept your invite: {link}\n\n"
        f"Token: {token}\n"
        f"Invited by: {inviter_name or 'a teammate'}\n"
    )
    html = f"""
    <p>You have been invited to join <strong>{org_name}</strong> as <strong>{role}</strong>.</p>
    <p><a href="{link}">Accept invitation</a></p>
    <p style="color:#666;font-size:12px">Or use token: <code>{token}</code></p>
    """
    return await send_email(to=to, subject=subject, text_body=text, html_body=html)
