"""
SecureNet Backend — Email Utilities

SMTP runs in a worker thread so it never blocks the asyncio event loop.
Emails are only ever really sent: when delivery is turned off or not
configured, callers get EmailDeliveryError — nothing is faked or printed.
"""

import asyncio
import smtplib
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable, List, Optional, Sequence

from app.core.config import settings
from app.utils.logger import logger

_PLACEHOLDER_MARKERS = ("your-", "your_", "example", "placeholder", "changeme", "change-me", "xxxx")


def _looks_placeholder(value: str) -> bool:
    value = value.strip().lower()
    return not value or any(marker in value for marker in _PLACEHOLDER_MARKERS)


class EmailDeliveryError(RuntimeError):
    """Raised when an email could not be delivered."""


def email_delivery_status() -> str:
    """'enabled' | 'disabled' (EMAIL_ENABLED=false) | 'misconfigured' (no SMTP credentials)."""
    if not settings.EMAIL_ENABLED:
        return "disabled"
    if _looks_placeholder(settings.SMTP_USER) or "@" not in settings.SMTP_USER             or _looks_placeholder(settings.SMTP_PASSWORD):
        return "misconfigured"
    return "enabled"


@dataclass(frozen=True)
class Attachment:
    """A file attached to an email (e.g. the incident report)."""
    filename: str
    content: bytes
    mime_subtype: str = "octet-stream"   # "plain" for .txt, "pdf", "csv", ...


def _build(to_email: str, subject: str, text: str, html: str,
           attachments: Sequence[Attachment] = (), reply_to: Optional[str] = None) -> MIMEMultipart:
    body = MIMEMultipart("alternative")
    body.attach(MIMEText(text, "plain", "utf-8"))
    body.attach(MIMEText(html, "html", "utf-8"))
    if attachments:
        message = MIMEMultipart("mixed")
        message.attach(body)
        for item in attachments:
            if item.mime_subtype == "plain":
                part = MIMEText(item.content.decode("utf-8"), "plain", "utf-8")
            else:
                part = MIMEApplication(item.content, _subtype=item.mime_subtype)
            part.add_header("Content-Disposition", "attachment", filename=item.filename)
            message.attach(part)
    else:
        message = body
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    if reply_to:
        message["Reply-To"] = reply_to
    return message


def _send_many_sync(recipients: List[str], subject: str, text: str, html: str,
                    attachments: Sequence[Attachment] = (), reply_to: Optional[str] = None) -> List[str]:
    """Send one message per recipient over a single SMTP session. Returns failed addresses."""
    failed: List[str] = []
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        for rcpt in recipients:
            try:
                message = _build(rcpt, subject, text, html, attachments, reply_to)
                server.sendmail(settings.SMTP_FROM_EMAIL, [rcpt], message.as_string())
            except smtplib.SMTPException as exc:
                logger.error(f"Email to {rcpt} failed: {exc}")
                failed.append(rcpt)
    return failed


async def send_email(recipients: Iterable[str], subject: str, text: str, html: str,
                     attachments: Optional[Sequence[Attachment]] = None, reply_to: Optional[str] = None) -> None:
    """Send an email to each recipient. Raises EmailDeliveryError on failure
    (including when email delivery is turned off or not configured)."""
    rcpts = sorted({r.strip().lower() for r in recipients if r and r.strip()})
    if not rcpts:
        return
    status = email_delivery_status()
    if status == "disabled":
        raise EmailDeliveryError("Email delivery is turned off (EMAIL_ENABLED=false in backend/.env)")
    if status == "misconfigured":
        raise EmailDeliveryError("SMTP_USER / SMTP_PASSWORD in backend/.env are not set to a real account")
    try:
        failed = await asyncio.to_thread(_send_many_sync, rcpts, subject, text, html, tuple(attachments or ()), reply_to)
    except Exception as exc:
        raise EmailDeliveryError(str(exc)) from exc
    if failed:
        raise EmailDeliveryError(f"Delivery failed for: {', '.join(failed)}")
    logger.info(f"Email sent to {len(rcpts)} recipient(s): {subject}")


async def _send_code(email: str, code: str, subject: str, heading: str, next_step: str) -> None:
    text = (
        f"Your {settings.APP_NAME} verification code is: {code}\n\n"
        f"{next_step}\n"
        f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
        "If you didn't request this code, please ignore this email."
    )
    html = f"""
    <html><body style="font-family:Arial,sans-serif">
      <h2>{settings.APP_NAME} - {heading}</h2>
      <p>Your verification code is:</p>
      <h1 style="font-size:32px;letter-spacing:8px;color:#0ea5e9;">{code}</h1>
      <p>{next_step}</p>
      <p>This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.</p>
      <p>If you didn't request this code, please ignore this email.</p>
    </body></html>
    """
    await send_email([email], f"{settings.APP_NAME} - {subject}", text, html)


async def send_otp_email(email: str, otp_code: str) -> None:
    """Registration code. Raises EmailDeliveryError if it cannot be sent."""
    await _send_code(email, otp_code, "Verification Code", "Email Verification",
                     f"Enter it on the {settings.APP_NAME} sign-up page, then create your password.")


async def send_password_reset_email(email: str, otp_code: str) -> None:
    """Forgot-password code. Raises EmailDeliveryError if it cannot be sent."""
    await _send_code(email, otp_code, "Password Reset Code", "Password Reset",
                     f"Enter it on the {settings.APP_NAME} forgot-password page, then choose a new password.")


async def send_profile_change_email(email: str, otp_code: str, summary: str) -> None:
    """Code confirming a change of the user's own details. Raises EmailDeliveryError."""
    await _send_code(email, otp_code, "Confirm your profile change", "Profile Change",
                     f"You asked to change your {summary}. Enter this code on the {settings.APP_NAME} Account page "
                     "to confirm. If this was not you, ignore this email and nothing will change.")
