"""
SecureNet — Alert e-mail notifier

Every stored security event is handed to `notifier.enqueue(event)` by the IDS.
The notifier:
  * collects alerts for ALERT_EMAIL_BATCH_SECONDS and then sends ONE email per
    recipient listing them (an attack burst never floods inboxes);
  * filters by Settings → Notifications (high / medium / blocked);
  * sends to every registered, active user's email address plus the optional
    extra recipient configured in Settings;
  * sends a periodic digest when "digest" is enabled.

In-app / desktop pop-ups are handled by the frontend from the WebSocket
`alert` messages; this module is only about email.
"""

from __future__ import annotations

import asyncio
import html
import platform
import socket
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
        )

    @property
    def title(self) -> str:
        return self.attack_type or "Unclassified anomaly"


def wanted(alert: AlertInfo, prefs: NotificationSettings) -> bool:
    """Does this alert match the notification preferences?"""
    return (
        (alert.severity == SeverityLevel.HIGH.value and prefs.alert_on_high)
        or (alert.severity == SeverityLevel.MEDIUM.value and prefs.alert_on_medium)
        or (alert.severity == SeverityLevel.LOW.value and prefs.alert_on_low)
        or (alert.action == ActionTaken.BLOCKED.value and prefs.alert_on_block)
    )


async def split_recipients(db, prefs: Optional[NotificationSettings]):
    """(user emails, admin emails, registered users). Every active user gets the
    normal alert; admins get the detailed admin version instead. The optional
    extra address from Settings gets the normal alert."""
    users = (await db.execute(
        select(User).where(User.account_status == AccountStatus.ACTIVE).order_by(User.created_at)
    )).scalars().all()
    admins = {u.email.strip().lower() for u in users if u.role == UserRole.ADMIN}
    regular = {u.email.strip().lower() for u in users if u.role != UserRole.ADMIN}
    if prefs is not None and prefs.email_address:
        extra = prefs.email_address.strip().lower()
        if extra not in admins:
            regular.add(extra)
    return sorted(regular), sorted(admins), list(users)


async def get_recipients(db, prefs: Optional[NotificationSettings]) -> List[str]:
    """All active registered users + the optional extra address from Settings."""
    rows = await db.execute(select(User.email).where(User.account_status == AccountStatus.ACTIVE))
    recipients = {email.strip().lower() for (email,) in rows if email}
    if prefs is not None and prefs.email_address:
        recipients.add(prefs.email_address.strip().lower())
    return sorted(recipients)


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
            f"[{a.severity.upper()}] {a.title} — {a.source_ip}:{a.source_port} → "
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
          <th style="padding:8px">Severity</th><th style="padding:8px">Attack</th><th style="padding:8px">Flow</th>
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
        return f"[{settings.APP_NAME}] Attack detected ({worst.severity.upper()}): {worst.title} from {worst.source_ip}"
    extra = f" ({high} HIGH)" if high else ""
    return f"[{settings.APP_NAME}] {len(alerts)} attacks detected{extra} — most severe: {worst.title}"


# ── Notifier service ─────────────────────────────────────────────────────────

async def fetch_events(db, alerts: Sequence[AlertInfo]) -> List[SecurityEvent]:
    ids = [uuid.UUID(a.event_id) for a in alerts]
    events = (await db.execute(select(SecurityEvent).where(SecurityEvent.id.in_(ids)))).scalars().all()
    return sorted(events, key=lambda e: e.timestamp)


def host_details() -> str:
    try:
        name = socket.gethostname()
    except OSError:
        name = "unknown"
    return f"{name} ({platform.system()} {platform.release()})"


def _role_label(user: User) -> str:
    return "Admin" if user.role == UserRole.ADMIN else "SecureNet User"


def render_admin_email(events: Sequence[SecurityEvent], heading: str, registered: Sequence[User],
                       operator: Optional[dict], host: str) -> tuple[str, str]:
    """The admin's copy: who was using SecureNet, the monitored computer, every
    registered user notified, and full details of each event."""
    offset = server_offset_minutes()

    def when(dt):
        return f"{to_local(dt, offset):%d %b %Y, %H:%M:%S} ({tz_label(offset)})"

    if operator:
        op = (f"{operator.get('name')} <{operator.get('email')}>, phone {operator.get('phone') or '-'} "
              f"({'Admin' if operator.get('role') == 'admin' else 'SecureNet User'})")
    else:
        op = "not recorded (the IDS was not turned on from the dashboard)"

    text = [heading, "ADMIN COPY - includes user and event details.", "",
            f"IDS turned on by  : {op}", f"Monitored computer: {host}", "",
            f"Registered users notified ({len(registered)}):"]
    text += [f"  - {u.full_name} <{u.email}>, phone {u.phone_number or '-'}, {_role_label(u)}" for u in registered]
    text += ["", f"Event details ({len(events)}):"]

    blocks = []
    for e in events:
        names = [f.get("name") for f in (e.contributing_features or []) if isinstance(f, dict) and f.get("name")]
        def count(n, word):
            return f"{n} {word}{'' if n == 1 else 's'}"

        traffic = [x for x in (
            f"{count(e.packets_sent, 'packet')} out" if e.packets_sent is not None else "",
            f"{count(e.packets_received, 'packet')} in" if e.packets_received is not None else "",
            f"{count(e.bytes_sent, 'byte')} out" if e.bytes_sent is not None else "",
            f"{count(e.bytes_received, 'byte')} in" if e.bytes_received is not None else "",
            f"{e.flow_duration_ms} ms long" if e.flow_duration_ms is not None else "",
        ) if x]
        fields = [
            ("Event ID", str(e.id)),
            ("Time", when(e.timestamp)),
            ("Attack", e.attack_type or "Unclassified anomaly"),
            ("Severity", e.severity.value.upper()),
            ("Confidence", f"{e.confidence * 100:.0f}%" if e.confidence is not None else "-"),
            ("Anomaly score", f"{e.anomaly_score:.3f}"),
            ("Source", f"{e.source_ip}:{e.source_port}"),
            ("Destination", f"{e.destination_ip}:{e.destination_port} ({e.protocol.value})"),
            ("Action / status", f"{e.action_taken.value} / {e.state.value.replace('_', ' ')}"),
            ("Reason", e.detection_reason or "-"),
            ("Unusual features", ", ".join(names) or "-"),
            ("Traffic", ", ".join(traffic) or "-"),
        ]
        text.append("")
        text += [f"  {k:16}: {v}" for k, v in fields]
        cells = "".join(
            f"<tr><td style='color:#7d6154;padding:3px 12px 3px 0;white-space:nowrap;vertical-align:top'>{_esc(k)}</td>"
            f"<td style='padding:3px 0'>{_esc(v)}</td></tr>" for k, v in fields)
        blocks.append(f"<table style='width:100%;font-size:13px;border-top:1px solid #efd6c6;margin-top:10px;"
                      f"padding-top:8px'>{cells}</table>")
    text += ["", "The full incident report is attached to this email."]

    users_html = "".join(
        f"<tr><td style='padding:3px 12px 3px 0'>{_esc(u.full_name)}</td>"
        f"<td style='padding:3px 12px 3px 0'>{_esc(u.email)}</td>"
        f"<td style='padding:3px 12px 3px 0'>{_esc(u.phone_number or '-')}</td>"
        f"<td style='padding:3px 0'>{_role_label(u)}</td></tr>" for u in registered)
    body = f"""<html><body style="margin:0;background:#fbeee4;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:760px;margin:0 auto;padding:24px;color:#3d2b22">
    <div style="color:#c2562f;font-size:20px;font-weight:bold;margin-bottom:4px">{_esc(settings.APP_NAME)} - admin alert</div>
    <div style="background:#fffaf6;border:1px solid #efd6c6;border-radius:8px;padding:20px">
      <h2 style="margin:0 0 6px">{_esc(heading)}</h2>
      <p style="margin:0 0 16px;color:#7d6154">Admin copy - includes user and event details.</p>
      <table style="font-size:13px;margin-bottom:12px">
        <tr><td style="color:#7d6154;padding:3px 12px 3px 0">IDS turned on by</td><td>{_esc(op)}</td></tr>
        <tr><td style="color:#7d6154;padding:3px 12px 3px 0">Monitored computer</td><td>{_esc(host)}</td></tr>
      </table>
      <h3 style="margin:16px 0 6px;font-size:14px">Registered users notified ({len(registered)})</h3>
      <table style="font-size:13px">{users_html}</table>
      <h3 style="margin:18px 0 0;font-size:14px">Event details ({len(events)})</h3>
      {''.join(blocks)}
      <p style="margin-top:16px;color:#5a4035">The full incident report is attached to this email.</p>
    </div>
  </div></body></html>"""
    return "\n".join(text), body


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
            user_rcpts, admin_rcpts, registered = await split_recipients(db, prefs)
            if not user_rcpts and not admin_rcpts:
                return 0
            events = await fetch_events(db, alerts)

        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        heading = (
            f"Attack detected: {alerts[0].title}" if len(alerts) == 1
            else f"{len(alerts)} attacks detected"
        )
        report = await asyncio.to_thread(report_attachment, events)
        subject = alert_subject(alerts)
        mails = []
        if user_rcpts:
            text, body = render_alert_email(alerts, heading)
            mails.append((user_rcpts, subject, text, body))
        if admin_rcpts:
            from app.ml.ids_service import get_ids_service  # late import: ids_service imports this module
            operator = get_ids_service().started_by
            text, body = render_admin_email(events, heading, registered, operator, host_details())
            admin_subject = subject.replace(f"[{settings.APP_NAME}]", f"[{settings.APP_NAME} Admin]", 1)
            mails.append((admin_rcpts, admin_subject, text, body))
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
