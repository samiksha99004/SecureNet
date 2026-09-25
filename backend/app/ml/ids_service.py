"""
SecureNet — IDS service (live detection loop)

Pipeline for every finished network flow (paper, Algorithm 1):

    capture thread ──FlowRecord──▶ asyncio queue ──▶ worker
        worker: whitelist check → Detector.analyze (thread pool)
              → broadcast live score → if alert: store SecurityEvent,
                apply Protection mode, notify, broadcast alert

Modes:
    OFF      – IDS stopped (no capture)
    monitor  – "Detection" mode: score, store and alert
    protect  – "Protection" mode: as monitor + automatic IP blocking

If no model is loaded the IDS still captures and counts flows, but nothing is
scored — the status endpoint reports `detector = "none"`.
"""

from __future__ import annotations

import asyncio
import ipaddress
import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.ml.detector import Detection, get_detector
from app.ml.features import FlowRecord
from app.ml.network_monitor import CaptureUnavailable, NetworkMonitor
from app.ml.protection import FirewallBlocker
from app.models.security_event import (
    ActionTaken, DetectionMode, EventState, Protocol, SecurityEvent, SeverityLevel,
)
from app.models.settings import (
    DetectionSettings, ProtectionSettings, WhitelistEntry, WhitelistEntryType,
)
from app.utils.logger import logger
from app.utils.timeutil import to_iso_z, utcnow
from app.services.notifier import get_notifier
from app.websocket.manager import manager

QUEUE_SIZE = 10_000


def alert_payload(event: SecurityEvent) -> dict:
    """WebSocket `alert` payload (same shape as GET /api/notifications items)."""
    title = event.attack_type or "Unclassified anomaly"
    return {
        "eventId": str(event.id),
        "timestamp": to_iso_z(event.timestamp),
        "severity": event.severity.value,
        "attackType": event.attack_type,
        "sourceIp": event.source_ip,
        "sourcePort": event.source_port,
        "destinationIp": event.destination_ip,
        "destinationPort": event.destination_port,
        "protocol": event.protocol.value,
        "anomalyScore": round(float(event.anomaly_score), 4),
        "actionTaken": event.action_taken.value,
        "message": f"{title} from {event.source_ip} → {event.destination_ip}:{event.destination_port} "
                   f"(score {event.anomaly_score:.2f}, {event.action_taken.value})",
    }


@dataclass
class IDSConfig:
    """Runtime configuration, refreshed from the Settings tables."""
    detection_enabled: bool = True
    anomaly_threshold: float = settings.ANOMALY_THRESHOLD
    stage2_enabled: bool = True
    stage2_confidence: float = settings.CLASSIFICATION_CONFIDENCE_THRESHOLD
    default_mode: DetectionMode = DetectionMode.MONITOR
    auto_block: bool = False
    auto_block_severities: set = field(default_factory=lambda: {"high"})
    block_duration_seconds: int = 3600
    max_blocked_ips: int = 1000
    wl_ips: set = field(default_factory=set)
    wl_networks: list = field(default_factory=list)
    wl_ports: set = field(default_factory=set)
    wl_protocols: set = field(default_factory=set)


class IDSService:
    def __init__(self) -> None:
        self.detector = get_detector()
        self.config = IDSConfig()
        self.mode: DetectionMode = DetectionMode.MONITOR
        self.enabled = False
        self.monitor: Optional[NetworkMonitor] = None
        self.blocker = FirewallBlocker()
        self.capture_error: Optional[str] = None
        self.started_at: Optional[float] = None
        # Who turned the IDS on (shown in the admin's alert email)
        self.started_by: Optional[dict] = None

        self._queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tasks: list[asyncio.Task] = []
        self._lifecycle_lock = asyncio.Lock()
        self._last_score_times: list[float] = []

        self.flows_analyzed = 0
        self.flows_dropped = 0
        self.anomalies_detected = 0
        self.attacks_detected = 0

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Called at app startup: load models only if ML_AUTOLOAD is set."""
        if settings.ML_AUTOLOAD:
            await self.reload_models()
        else:
            logger.info("ML_AUTOLOAD=false — no detection model loaded (IDS will run capture-only)")
        try:
            await self.reload_config()
        except Exception as exc:  # DB may be unreachable at boot; retried on start
            logger.warning(f"Could not load IDS settings at startup: {exc}")
        self.mode = self.config.default_mode

    async def reload_models(self) -> bool:
        loaded = await asyncio.to_thread(self.detector.load, settings.models_dir)
        await self.broadcast_status()
        return loaded

    async def start(self, mode: Optional[str] = None) -> None:
        """Start capture + detection. Raises CaptureUnavailable on failure."""
        # One start/stop at a time: two quick "ON" clicks (or two users) must not
        # both pass the `enabled` check and leave a second sniffer running.
        async with self._lifecycle_lock:
            if self.enabled:
                if mode:
                    await self.set_mode(mode)
                return
            await self.reload_config()
            await self.set_mode(mode or self.config.default_mode.value)

            self._loop = asyncio.get_running_loop()
            self._queue = asyncio.Queue(maxsize=QUEUE_SIZE)
            self.monitor = NetworkMonitor(
                on_flow=self._enqueue_from_thread,
                interface=settings.CAPTURE_INTERFACE or None,
                idle_timeout=settings.FLOW_IDLE_TIMEOUT_SECONDS,
                active_timeout=settings.FLOW_ACTIVE_TIMEOUT_SECONDS,
            )
            try:
                await asyncio.to_thread(self.monitor.start)
            except CaptureUnavailable as exc:
                self.capture_error = str(exc)
                self.monitor = None
                logger.error(f"IDS start failed: {exc}")
                raise

            self.capture_error = None
            self.enabled = True
            self.started_at = time.time()
            self._tasks = [
                asyncio.create_task(self._worker(), name="ids-worker"),
                asyncio.create_task(self._maintenance(), name="ids-maintenance"),
            ]
            logger.info(f"IDS started (mode={self.mode.value}, detector={self.detector.name})")
        await self.broadcast_status()

    async def stop(self) -> None:
        async with self._lifecycle_lock:
            if not self.enabled:
                return
            self.enabled = False
            monitor, self.monitor = self.monitor, None
            if monitor is not None:
                await asyncio.to_thread(monitor.stop)
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks = []
            await self.blocker.unblock_all()
            self.started_at = None
            logger.info("IDS stopped")
        await self.broadcast_status()

    async def set_mode(self, mode: str) -> None:
        try:
            self.mode = DetectionMode(mode)
        except ValueError:
            raise ValueError(f"Unknown mode '{mode}' (expected 'monitor' or 'protect')")
        if self.mode != DetectionMode.PROTECT:
            await self.blocker.unblock_all()

    # ── configuration ────────────────────────────────────────────────────────

    async def reload_config(self) -> None:
        """Pull detection/protection/notification settings and the whitelist from the DB."""
        cfg = IDSConfig()
        async with AsyncSessionLocal() as db:
            det = (await db.execute(select(DetectionSettings).limit(1))).scalars().first()
            prot = (await db.execute(select(ProtectionSettings).limit(1))).scalars().first()
            entries = (await db.execute(select(WhitelistEntry).where(WhitelistEntry.active.is_(True)))).scalars().all()

        if det:
            cfg.detection_enabled = det.enabled
            cfg.anomaly_threshold = det.anomaly_threshold
            cfg.stage2_enabled = det.stage2_enabled
            cfg.stage2_confidence = det.stage2_confidence_threshold
        if prot:
            cfg.default_mode = DetectionMode(prot.mode.value)
            cfg.auto_block = prot.auto_block
            cfg.auto_block_severities = set(prot.auto_block_severities or [])
            cfg.block_duration_seconds = prot.block_duration_seconds
            cfg.max_blocked_ips = prot.max_blocked_ips
        else:
            cfg.default_mode = DetectionMode(settings.DETECTION_MODE if settings.DETECTION_MODE in ("monitor", "protect") else "monitor")
        for entry in entries:
            try:
                if entry.type == WhitelistEntryType.IP:
                    cfg.wl_ips.add(str(ipaddress.ip_address(entry.value)))
                elif entry.type == WhitelistEntryType.CIDR:
                    cfg.wl_networks.append(ipaddress.ip_network(entry.value, strict=False))
                elif entry.type == WhitelistEntryType.PORT:
                    cfg.wl_ports.add(int(entry.value))
                elif entry.type == WhitelistEntryType.PROTOCOL:
                    cfg.wl_protocols.add(entry.value.upper())
            except ValueError:
                logger.warning(f"Ignoring invalid whitelist entry {entry.type.value}:{entry.value}")
        self.config = cfg

    def is_whitelisted(self, flow: FlowRecord) -> bool:
        cfg = self.config
        if flow.protocol_name.upper() in cfg.wl_protocols:
            return True
        if flow.src_port in cfg.wl_ports or flow.dst_port in cfg.wl_ports:
            return True
        for ip in (flow.src_ip, flow.dst_ip):
            if ip in cfg.wl_ips:
                return True
            try:
                addr = ipaddress.ip_address(ip)
            except ValueError:
                continue
            if any(addr in net for net in cfg.wl_networks if net.version == addr.version):
                return True
        return False

    # ── status ───────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        monitor = self.monitor
        return {
            "enabled": self.enabled,
            "mode": self.mode.value,
            "ml_loaded": self.detector.loaded,
            "detector": self.detector.name,
            "capture_active": bool(monitor and monitor.running),
            "capture_error": self.capture_error or (monitor.last_error if monitor else None),
            "packets_processed": monitor.packet_count if monitor else 0,
            "flows_analyzed": self.flows_analyzed,
            "active_flows": monitor.active_flow_count if monitor else 0,
            "anomalies_detected": self.anomalies_detected,
            "attacks_detected": self.attacks_detected,
            "blocked_ips": len(self.blocker.blocked),
            "uptime_seconds": int(time.time() - self.started_at) if self.started_at else 0,
        }

    async def broadcast_status(self) -> None:
        status = self.get_status()
        await manager.send_system_status({
            "detectionEnabled": status["enabled"],
            "mode": status["mode"],
            "modelStatus": status["detector"],
            "activeFlows": status["active_flows"],
        })

    # ── flow processing ──────────────────────────────────────────────────────

    def _enqueue_from_thread(self, record: FlowRecord) -> None:
        """Called from the capture threads — hand the record to the event loop."""
        loop, queue = self._loop, self._queue
        if loop is None or queue is None or loop.is_closed():
            return

        def _put() -> None:
            try:
                queue.put_nowait(record)
            except asyncio.QueueFull:
                self.flows_dropped += 1

        loop.call_soon_threadsafe(_put)

    async def _worker(self) -> None:
        assert self._queue is not None
        while True:
            record = await self._queue.get()
            try:
                await self.process_flow(record)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(f"Flow processing error: {exc}", exc_info=True)
            finally:
                self._queue.task_done()

    async def _maintenance(self) -> None:
        while True:
            await asyncio.sleep(5)
            await self.blocker.unblock_expired()
            await self.broadcast_status()

    async def process_flow(self, flow: FlowRecord) -> Optional[SecurityEvent]:
        """Run one finished flow through the detection pipeline."""
        self.flows_analyzed += 1
        if self.is_whitelisted(flow) or not self.config.detection_enabled or not self.detector.loaded:
            return None

        cfg = self.config
        detection: Optional[Detection] = await asyncio.to_thread(
            self.detector.analyze, flow.features, cfg.anomaly_threshold, cfg.stage2_enabled, cfg.stage2_confidence
        )
        if detection is None:
            return None

        severity = self._severity(detection.anomaly_score, cfg.anomaly_threshold)
        if not detection.is_alert:
            await self._broadcast_score(flow, detection, severity, throttle=True)
            return None

        self.anomalies_detected += 1
        if detection.attack_type:
            self.attacks_detected += 1

        action = ActionTaken.ALERTED
        reason = detection.reason
        if (
            self.mode == DetectionMode.PROTECT
            and cfg.auto_block
            and severity.value in cfg.auto_block_severities
        ):
            blocked, note = await self.blocker.block(flow.src_ip, cfg.block_duration_seconds, cfg.max_blocked_ips)
            action = ActionTaken.BLOCKED if blocked else ActionTaken.ALERTED
            reason = f"{reason}. Protection: {note}"

        event = SecurityEvent(
            timestamp=utcnow(),
            source_ip=flow.src_ip,
            source_port=flow.src_port,
            destination_ip=flow.dst_ip,
            destination_port=flow.dst_port,
            protocol=Protocol(flow.protocol_name) if flow.protocol_name in ("TCP", "UDP", "ICMP") else Protocol.OTHER,
            anomaly_score=round(detection.anomaly_score, 6),
            severity=severity,
            attack_type=detection.attack_type,
            confidence=detection.confidence,
            mode=self.mode,
            state=EventState.ACTIVE,
            action_taken=action,
            detection_reason=reason,
            contributing_features=detection.top_features or None,
            flow_duration_ms=flow.duration_ms,
            bytes_sent=flow.fwd_bytes,
            bytes_received=flow.bwd_bytes,
            packets_sent=flow.fwd_packets,
            packets_received=flow.bwd_packets,
        )
        async with AsyncSessionLocal() as db:
            db.add(event)
            await db.commit()
            await db.refresh(event)

        await self._broadcast_score(flow, detection, severity, throttle=False)
        await manager.send_alert(alert_payload(event))
        get_notifier().enqueue(event)
        logger.info(f"Alert: {event.attack_type or 'anomaly'} from {flow.src_ip} "
                    f"score={detection.anomaly_score:.3f} severity={severity.value} action={action.value}")
        return event

    @staticmethod
    def _severity(score: float, threshold: float) -> SeverityLevel:
        """Severity from how far the score is above the threshold."""
        span = max(1.0 - threshold, 1e-6)
        relative = (score - threshold) / span
        if relative >= 0.5:
            return SeverityLevel.HIGH
        if relative >= 0.2:
            return SeverityLevel.MEDIUM
        return SeverityLevel.LOW

    async def _broadcast_score(self, flow: FlowRecord, detection: Detection, severity: SeverityLevel,
                               throttle: bool) -> None:
        if throttle:
            now = time.time()
            self._last_score_times = [t for t in self._last_score_times if now - t < 1.0]
            if len(self._last_score_times) >= settings.LIVE_SCORE_MAX_PER_SECOND:
                return
            self._last_score_times.append(now)
        await manager.send_live_score({
            "anomalyScore": round(detection.anomaly_score, 4),
            "severity": severity.value if detection.is_alert else "low",
            "isAlert": detection.is_alert,
            "sourceIp": flow.src_ip,
            "destinationIp": flow.dst_ip,
            "protocol": flow.protocol_name,
            "attackType": detection.attack_type,
        })


ids_service = IDSService()


def get_ids_service() -> IDSService:
    return ids_service
