"""
SecureNet — Alert e-mail notifier

Every stored security event is handed to `notifier.enqueue(event)` by the IDS.
The notifier:
  * collects alerts for ALERT_EMAIL_BATCH_SECONDS and then sends ONE email per
    recipient listing them (an attack burst never floods inboxes);
  * filters by Settings → Notifications (high / medium / blocked);
  * sends FROM the admin's Gmail (SMTP_USER) TO every active SecureNet user (and the
    optional extra address from Settings). The admin is the sender, not a user, and
    never receives attack emails;
  * sends a periodic digest when "digest" is enabled.

In-app / desktop pop-ups are handled by the frontend from the WebSocket
`alert` messages; this module is only about email.
"""

from __future__ import annotations

import asyncio
import html
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional, Sequence

from sqlalchemy import func, select

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.models.security_event import ActionTaken, SecurityEvent, SeverityLevel
from app.models.settings import NotificationSettings
from app.models.user import AccountStatus, User, UserRole
from app.services.incident_report import render_text, report_filename, server_offset_minutes, to_local, tz_label
from app.utils.email import Attachment, EmailDeliveryError, send_email
from app.utils.logger import logger
from app.services.verdict import ABNORMAL, guesses_text, possible_attack
from app.utils.timeutil import parse_iso_utc, to_iso_z, utcnow

SEVERITY_COLORS = {"high": "#dc2626", "medium": "#d97706", "low": "#059669"}


@dataclass
class AlertInfo:
    """Snapshot of a security event (safe to keep after the DB session closes)."""
    event_id: str
    timestamp: str
    severity: str
    attack_type: Optional[str]
    source_ip: str
    source_port: int
    destination_ip: str
    destination_port: int
    protocol: str
    anomaly_score: float
    action: str
    reason: Optional[str]
    confidence: Optional[float] = None
    guesses: Optional[list] = None

    @classmethod
    def from_event(cls, e: SecurityEvent) -> "AlertInfo":
        return cls(
            event_id=str(e.id),
            timestamp=to_iso_z(e.timestamp),
            severity=e.severity.value,
            attack_type=e.attack_type,
            source_ip=e.source_ip,
            source_port=e.source_port,
            destination_ip=e.destination_ip,
            destination_port=e.destination_port,
            protocol=e.protocol.value,
            anomaly_score=float(e.anomaly_score),
            action=e.action_taken.value,
            reason=e.detection_reason,
            confidence=e.confidence,
            guesses=e.attack_guesses,
        )

    @property
    def title(self) -> str:
        return ABNORMAL

    @property
    def guess(self) -> str:
        """The model's best guess of which attack it might be."""
        return possible_attack(self.attack_type, self.confidence, self.guesses)


def wanted(alert: AlertInfo, prefs: NotificationSettings) -> bool:
    """Does this alert match the notification preferences?"""
    return (
        (alert.severity == SeverityLevel.HIGH.value and prefs.alert_on_high)
        or (alert.severity == SeverityLevel.MEDIUM.value and prefs.alert_on_medium)
        or (alert.severity == SeverityLevel.LOW.value and prefs.alert_on_low)
        or (alert.action == ActionTaken.BLOCKED.value and prefs.alert_on_block)
    )


async def get_recipients(db, prefs: Optional[NotificationSettings]) -> List[str]:
    """Who gets attack emails: every active SecureNet user who has them switched on, plus
    the optional extra address from Settings. Admins never do — the admin sends the alerts
    (from SMTP_USER); an extra address that belongs to an admin is ignored too."""
    users = (await db.execute(
        select(User.email, User.role, User.email_alerts).where(User.account_status == AccountStatus.ACTIVE)
    )).all()
    admins = {email.strip().lower() for email, role, _ in users if email and role == UserRole.ADMIN}
    admins |= settings.admin_emails
    recipients = {email.strip().lower() for email, role, wants in users
                  if email and wants and role != UserRole.ADMIN}
    if prefs is not None and prefs.email_address:
        extra = prefs.email_address.strip().lower()
        if extra not in admins:
            recipients.add(extra)
    return sorted(recipients - admins)


# ── Email rendering ──────────────────────────────────────────────────────────

def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}


def most_severe(alerts: Sequence[AlertInfo]) -> AlertInfo:
    return max(alerts, key=lambda a: (SEVERITY_RANK.get(a.severity, 0), a.timestamp))


def local_time(iso: str) -> str:
    """Alert time in the backend machine's local time zone, e.g. 25 Sep 2026, 16:29:11 (UTC+05:30)."""
    offset = server_offset_minutes()
    return f"{to_local(parse_iso_utc(iso), offset):%d %b %Y, %H:%M:%S} ({tz_label(offset)})"


def render_alert_email(alerts: Sequence[AlertInfo], heading: str) -> tuple[str, str]:
    """Return (text, html) bodies for a list of alerts."""
    shown = list(alerts)[: settings.ALERT_EMAIL_MAX_EVENTS]
    hidden = len(alerts) - len(shown)

    text_lines = [heading, ""]
    for a in shown:
        text_lines.append(
            f"[{a.severity.upper()}] {a.title} (possible attack: {a.guess}) — {a.source_ip}:{a.source_port} → "
            f"{a.destination_ip}:{a.destination_port} ({a.protocol}) score {a.anomaly_score:.3f}, "
            f"at {local_time(a.timestamp)}"
        )
    if hidden:
        text_lines.append(f"... and {hidden} more")
    text_lines += ["", "The full incident report is attached to this email.",
                   f"Open the dashboard: {settings.DASHBOARD_URL}/history"]

    rows = "".join(
        f"""<tr>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0">
            <span style="background:{SEVERITY_COLORS.get(a.severity, '#64748b')};color:#fff;border-radius:4px;
                         padding:2px 6px;font-size:11px;font-weight:bold">{_esc(a.severity.upper())}</span></td>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0"><b>{_esc(a.title)}</b><br>
            Possible attack: {_esc(a.guess)}<br>
            <span style="color:#64748b;font-size:12px">{_esc(a.reason or '')}</span></td>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0;font-family:monospace">
            {_esc(a.source_ip)}:{a.source_port}<br>→ {_esc(a.destination_ip)}:{a.destination_port} {_esc(a.protocol)}</td>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0;font-family:monospace">{a.anomaly_score:.3f}</td>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0">{_esc(a.action)}</td>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0;font-size:12px">{_esc(local_time(a.timestamp))}</td>
        </tr>"""
        for a in shown
    )
    more = f"<p style='color:#64748b'>… and {hidden} more alert(s).</p>" if hidden else ""
    body = f"""<html><body style="margin:0;background:#0a1020;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:760px;margin:0 auto;padding:24px">
    <div style="color:#38bdf8;font-size:20px;font-weight:bold;margin-bottom:4px">🛡 {_esc(settings.APP_NAME)}</div>
    <div style="background:#ffffff;border-radius:8px;padding:20px">
      <h2 style="margin:0 0 12px;color:#0f172a">{_esc(heading)}</h2>
      <table style="width:100%;border-collapse:collapse;font-size:13px;color:#0f172a">
        <tr style="text-align:left;color:#64748b;font-size:11px;text-transform:uppercase">
          <th style="padding:8px">Severity</th><th style="padding:8px">Verdict</th><th style="padding:8px">Flow</th>
          <th style="padding:8px">Score</th><th style="padding:8px">Action</th><th style="padding:8px">Time</th></tr>
        {rows}
      </table>
      {more}
      <p style="margin-top:16px;color:#334155">The full incident report is attached to this email.</p>
      <p style="margin-top:12px"><a href="{_esc(settings.DASHBOARD_URL)}/history"
         style="background:#0ea5e9;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">
         Open SecureNet dashboard</a></p>
    </div>
    <p style="color:#64748b;font-size:11px">You receive this because you are a registered SecureNet user.</p>
  </div></body></html>"""
    return "\n".join(text_lines), body


def alert_subject(alerts: Sequence[AlertInfo]) -> str:
    high = sum(1 for a in alerts if a.severity == "high")
    worst = most_severe(alerts)
    if len(alerts) == 1:
        return (f"[{settings.APP_NAME}] {ABNORMAL} ({worst.severity.upper()}) from {worst.source_ip}"
                f" — possible attack: {worst.guess}")
    extra = f" ({high} HIGH)" if high else ""
    return (f"[{settings.APP_NAME}] {ABNORMAL}: {len(alerts)} alerts{extra}"
            f" — most severe possible attack: {worst.guess}")


# ── Notifier service ─────────────────────────────────────────────────────────

async def fetch_events(db, alerts: Sequence[AlertInfo]) -> List[SecurityEvent]:
    ids = [uuid.UUID(a.event_id) for a in alerts]
    events = (await db.execute(select(SecurityEvent).where(SecurityEvent.id.in_(ids)))).scalars().all()
    return sorted(events, key=lambda e: e.timestamp)


def report_attachment(events: Sequence[SecurityEvent]) -> Attachment:
    """Incident report (.txt) for the attacks in one alert email."""
    offset = server_offset_minutes()
    stamp = to_local(utcnow(), offset).strftime("%Y%m%d-%H%M%S")
    title = f"Attack alert - {len(events)} incident(s)"
    content = render_text(events, title, offset)
    return Attachment(report_filename("incident-report", stamp, "txt"), content.encode("utf-8"), "plain")


class AlertNotifier:
    def __init__(self) -> None:
        self._pending: List[AlertInfo] = []
        self._wakeup = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._last_digest = time.time()
        self.emails_sent = 0
        self.last_error: Optional[str] = None

    def enqueue(self, event: SecurityEvent) -> None:
        """Queue a stored security event for the next alert email."""
        self._pending.append(AlertInfo.from_event(event))
        self._wakeup.set()

    async def start(self) -> None:
        if self._task is None:
            self._wakeup = asyncio.Event()
            self._task = asyncio.create_task(self._run(), name="alert-notifier")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        await self.flush()  # don't lose alerts queued right before shutdown

    async def _run(self) -> None:
        while True:
            try:
                await asyncio.wait_for(self._wakeup.wait(), timeout=60)
                # Batch window: let a burst of alerts accumulate into one email
                await asyncio.sleep(settings.ALERT_EMAIL_BATCH_SECONDS)
            except asyncio.TimeoutError:
                pass
            self._wakeup.clear()
            try:
                await self.flush()
                await self._maybe_send_digest()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # never let the notifier die
                self.last_error = str(exc)
                logger.error(f"Alert notifier error: {exc}", exc_info=True)

    async def flush(self) -> int:
        """Send pending alerts now. Returns the number of alerts emailed."""
        pending, self._pending = self._pending, []
        if not pending:
            return 0
        async with AsyncSessionLocal() as db:
            prefs = (await db.execute(select(NotificationSettings).limit(1))).scalars().first()
            if prefs is None or not prefs.email_enabled:
                return 0
            alerts = [a for a in pending if wanted(a, prefs)]
            if not alerts:
                return 0
            recipients = await get_recipients(db, prefs)
            if not recipients:
                return 0
            events = await fetch_events(db, alerts)

        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        heading = (
            f"{ABNORMAL} — possible attack: {alerts[0].guess}" if len(alerts) == 1
            else f"{ABNORMAL}: {len(alerts)} alerts"
        )
        report = await asyncio.to_thread(report_attachment, events)
        subject = alert_subject(alerts)
        text, body = render_alert_email(alerts, heading)
        mails = [(recipients, subject, text, body)]
        for rcpts, subj, text, body in mails:
            try:
                await send_email(rcpts, subj, text, body, attachments=[report])
                self.emails_sent += 1
                self.last_error = None
            except EmailDeliveryError as exc:
                self.last_error = str(exc)
                logger.error(f"Alert email failed: {exc}")
        return len(alerts)

    async def _maybe_send_digest(self) -> None:
        async with AsyncSessionLocal() as db:
            prefs = (await db.execute(select(NotificationSettings).limit(1))).scalars().first()
            if prefs is None or not prefs.email_enabled or not prefs.digest_enabled:
                return
            interval = max(1, prefs.digest_interval_hours) * 3600
            if time.time() - self._last_digest < interval:
                return
            self._last_digest = time.time()
            since = utcnow() - timedelta(seconds=interval)
            events = (await db.execute(
                select(SecurityEvent).where(SecurityEvent.timestamp >= since)
                .order_by(SecurityEvent.timestamp.desc()).limit(settings.ALERT_EMAIL_MAX_EVENTS)
            )).scalars().all()
            total = (await db.execute(
                select(func.count()).select_from(SecurityEvent).where(SecurityEvent.timestamp >= since)
            )).scalar() or 0
            recipients = await get_recipients(db, prefs)
            alerts = [AlertInfo.from_event(e) for e in events]
        if not recipients:
            return
        hours = prefs.digest_interval_hours
        if not alerts:
            text = f"No security events were detected in the last {hours} hour(s)."
            body = f"<html><body style='font-family:Arial'><h3>{_esc(settings.APP_NAME)} digest</h3><p>{text}</p></body></html>"
        else:
            text, body = render_alert_email(alerts, f"Digest: {total} security event(s) in the last {hours} hour(s)")
        try:
            await send_email(recipients, f"[{settings.APP_NAME}] Security digest — {total} event(s) in {hours}h",
                             text, body)
        except EmailDeliveryError as exc:
            self.last_error = str(exc)
            logger.error(f"Digest email failed: {exc}")


notifier = AlertNotifier()


def get_notifier() -> AlertNotifier:
    return notifier
