"""
SecureNet Backend — Email Utilities

SMTP runs in a worker thread so it never blocks the asyncio event loop.
Emails are only ever really sent: when delivery is turned off or not
configured, callers get EmailDeliveryError — nothing is faked or printed.
"""

import asyncio
import html as html_mod
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


def render_code_email(code: str, heading: str, next_step: str) -> tuple[str, str]:
    """(text, html) of a verification-code email.

    Layout like the big services' code emails: a grey "Code requested" panel
    with every digit in its own box and a "Copy code" button. Emails cannot
    run code, so the button is a link to SecureNet's /code page (the code is in
    the #fragment, never sent to a server): that page copies the code to the
    clipboard and fills it into the SecureNet tab that is waiting for it.
    Table-based with inline styles only, so Gmail / Outlook / phone mail apps
    show it the same way; the digits are also plain text that can be selected.
    """
    app = html_mod.escape(settings.APP_NAME)
    minutes = settings.OTP_EXPIRE_MINUTES
    copy_url = f"{settings.DASHBOARD_URL.rstrip('/')}/code#{code}"
    text = (
        f"Your {settings.APP_NAME} verification code is: {code}\n"
        f"Copy code: {copy_url}\n\n"
        f"{next_step}\n"
        f"This code expires in {minutes} minutes and works only once.\n"
        "If you didn't request this code, you can ignore this email."
    )
    digits = "".join(
        '<td style="padding:0 3px">'
        '<div style="width:34px;height:44px;line-height:44px;background:#ffffff;border:1px solid #d9dee6;'
        "border-radius:6px;text-align:center;font-family:Consolas,'Courier New',monospace;font-size:24px;"
        f'color:#1f2328">{html_mod.escape(ch)}</div></td>'
        for ch in code
    )
    body = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#ffffff;font-family:Arial,Helvetica,sans-serif;color:#1f2328">
<div style="display:none;max-height:0;overflow:hidden">Your {app} verification code is {code}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff">
  <tr><td align="center" style="padding:24px 12px">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px">
      <tr><td style="font-size:20px;font-weight:bold;color:#c2562f;padding:0 0 4px">&#128737; {app}</td></tr>
      <tr><td style="font-size:22px;padding:4px 0 16px">{html_mod.escape(heading)} verification code</td></tr>
      <tr><td style="background:#eef1f6;border-radius:12px;padding:20px 22px">
        <div style="font-size:15px;color:#3d444d;margin:0 0 12px">Code requested</div>
        <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px -3px"><tr>{digits}</tr></table>
        <table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="border-radius:22px;background:#0969da">
          <a href="{html_mod.escape(copy_url)}" target="_blank"
             style="display:inline-block;padding:11px 26px;border-radius:22px;background:#0969da;color:#ffffff;
                    font-size:16px;font-weight:bold;text-decoration:none">Copy code</a>
        </td></tr></table>
        <div style="font-size:12px;color:#59636e;margin:10px 0 0">Copies the code and fills it into SecureNet on this
          computer. On another device, type the digits above.</div>
      </td></tr>
      <tr><td style="font-size:14px;line-height:1.5;padding:18px 2px 0">
        <p style="margin:0 0 10px">{html_mod.escape(next_step)}</p>
        <p style="margin:0 0 10px">This code expires in <b>{minutes} minutes</b> and works only once.</p>
        <p style="margin:0;color:#59636e">If you didn't request this code, you can ignore this email.
           Never share this code with anyone.</p>
      </td></tr>
      <tr><td style="font-size:12px;color:#8c959f;padding:24px 2px 0;border-top:1px solid #e6e9ee">
        Sent by {app} - Behavioural Intrusion Detection System</td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""
    return text, body


async def _send_code(email: str, code: str, purpose: str, next_step: str) -> None:
    """Email a code. Subject "[SecureNet] <purpose> verification code" (like GitHub's), which
    also helps mail apps recognise it as a code email."""
    text, body = render_code_email(code, purpose, next_step)
    await send_email([email], f"[{settings.APP_NAME}] {purpose} verification code", text, body)


async def send_otp_email(email: str, otp_code: str) -> None:
    """Registration code. Raises EmailDeliveryError if it cannot be sent."""
    await _send_code(email, otp_code, "Sign-up",
                     f"Enter it on the {settings.APP_NAME} sign-up page, then create your password.")


async def send_password_reset_email(email: str, otp_code: str) -> None:
    """Forgot-password code. Raises EmailDeliveryError if it cannot be sent."""
    await _send_code(email, otp_code, "Password reset",
                     f"Enter it on the {settings.APP_NAME} forgot-password page, then choose a new password.")


async def send_login_code_email(email: str, otp_code: str) -> None:
    """Sign-in code (second step after the password). Raises EmailDeliveryError."""
    await _send_code(email, otp_code, "Sign-in",
                     f"Your password was just entered on the {settings.APP_NAME} sign-in page. Enter this code to "
                     "finish signing in. If this was not you, change your password right away - someone knows it.")


async def send_password_change_email(email: str, otp_code: str) -> None:
    """Code confirming a signed-in user's password change. Raises EmailDeliveryError."""
    await _send_code(email, otp_code, "Password change",
                     f"Someone signed in to your {settings.APP_NAME} account asked to change its password. Enter "
                     "this code on the Account page to confirm. If this was not you, ignore this email, keep your "
                     f"password and tell the {settings.APP_NAME} admin.")


async def send_profile_change_email(email: str, otp_code: str, summary: str) -> None:
    """Code confirming a change of the user's own details. Raises EmailDeliveryError."""
    await _send_code(email, otp_code, "Profile change",
                     f"You asked to change your {summary}. Enter this code on the {settings.APP_NAME} Account page "
                     "to confirm. If this was not you, ignore this email and nothing will change.")
