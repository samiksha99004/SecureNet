"""
SecureNet Backend — Dashboard Routes

KPIs, protocol distribution, top sources and host status.
Stored incident history is always shown (whether or not the IDS is running);
live-only figures (active flows) come from the running IDS.
"""

import platform
import time
from datetime import timedelta
from typing import List

import psutil
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.routes.events import convert_event_to_response
from app.core.config import settings
from app.db.base import get_db
from app.ml.ids_service import get_ids_service
from app.models.security_event import ActionTaken, EventState, Protocol, SecurityEvent, SeverityLevel
from app.models.user import User
from app.schemas.security import (
    AttackTypeCount,
    DashboardSummary,
    HostStatus,
    ProtocolDistribution,
    SeverityBreakdown,
    TopSource,
)
from app.utils.timeutil import utcnow

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Network throughput is derived from two psutil samples.
_net_sample: dict = {"time": None, "bytes": None}


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """KPIs and recent events.

    * activeFlows          – flows currently being tracked by the live IDS
    * anomaliesLastHour    – events stored in the last hour
    * highSeverityCount    – unresolved (active) high-severity events
    * blockedCount         – events whose source IP was blocked
    * averageAnomalyScore  – mean score of events in the last hour
    """
    one_hour_ago = utcnow() - timedelta(hours=1)

    async def scalar(query):
        return (await db.execute(query)).scalar() or 0

    anomalies_last_hour = await scalar(
        select(func.count()).select_from(SecurityEvent).where(SecurityEvent.timestamp >= one_hour_ago)
    )
    high_severity_count = await scalar(
        select(func.count()).select_from(SecurityEvent).where(
            SecurityEvent.severity == SeverityLevel.HIGH, SecurityEvent.state == EventState.ACTIVE
        )
    )
    blocked_count = await scalar(
        select(func.count()).select_from(SecurityEvent).where(SecurityEvent.action_taken == ActionTaken.BLOCKED)
    )
    avg_score = await scalar(
        select(func.avg(SecurityEvent.anomaly_score)).where(SecurityEvent.timestamp >= one_hour_ago)
    )

    severity_rows = await db.execute(
        select(SecurityEvent.severity, func.count())
        .where(SecurityEvent.state == EventState.ACTIVE)
        .group_by(SecurityEvent.severity)
    )
    severity_counts = {row[0]: row[1] for row in severity_rows}

    attack_rows = await db.execute(
        select(SecurityEvent.attack_type, func.count())
        .where(SecurityEvent.attack_type.isnot(None))
        .group_by(SecurityEvent.attack_type)
        .order_by(desc(func.count()))
        .limit(10)
    )

    recent = (await db.execute(
        select(SecurityEvent).order_by(desc(SecurityEvent.timestamp)).limit(10)
    )).scalars().all()

    return DashboardSummary(
        active_flows=get_ids_service().get_status()["active_flows"],
        anomalies_last_hour=anomalies_last_hour,
        high_severity_count=high_severity_count,
        blocked_count=blocked_count,
        average_anomaly_score=round(float(avg_score), 4),
        severity_breakdown=SeverityBreakdown(
            low=severity_counts.get(SeverityLevel.LOW, 0),
            medium=severity_counts.get(SeverityLevel.MEDIUM, 0),
            high=severity_counts.get(SeverityLevel.HIGH, 0),
        ),
        attack_type_distribution=[AttackTypeCount(attack_type=r[0], count=r[1]) for r in attack_rows],
        recent_events=[convert_event_to_response(e) for e in recent],
    )


@router.get("/host-status", response_model=HostStatus)
async def get_host_status(current_user: User = Depends(get_current_user)):
    """Current host resource usage (non-blocking psutil calls)."""
    try:
        now = time.monotonic()
        net = psutil.net_io_counters()
        total_bytes = net.bytes_sent + net.bytes_recv
        rate = None
        if _net_sample["time"] is not None and now > _net_sample["time"]:
            rate = max(0.0, (total_bytes - _net_sample["bytes"]) / (now - _net_sample["time"]))
        _net_sample.update(time=now, bytes=total_bytes)

        return HostStatus(
            hostname=platform.node(),
            os=f"{platform.system()} {platform.release()}",
            cpu_percent=round(psutil.cpu_percent(interval=None), 2),
            memory_percent=round(psutil.virtual_memory().percent, 2),
            network_interface=settings.CAPTURE_INTERFACE or "default",
            network_bytes_per_sec=round(rate, 1) if rate is not None else None,
            uptime=int(time.time() - psutil.boot_time()),
            last_updated=utcnow(),
        )
    except Exception:
        return HostStatus()


@router.get("/protocol-distribution", response_model=ProtocolDistribution)
async def get_protocol_distribution(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Protocol distribution of stored security events."""
    rows = await db.execute(select(SecurityEvent.protocol, func.count()).group_by(SecurityEvent.protocol))
    counts = {row[0]: row[1] for row in rows}
    tcp, udp = counts.get(Protocol.TCP, 0), counts.get(Protocol.UDP, 0)
    icmp, other = counts.get(Protocol.ICMP, 0), counts.get(Protocol.OTHER, 0)
    return ProtocolDistribution(tcp=tcp, udp=udp, icmp=icmp, other=other, total_flows=tcp + udp + icmp + other)


@router.get("/top-sources", response_model=List[TopSource])
async def get_top_sources(
    limit: int = Query(5, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Source IPs with the most security events."""
    from sqlalchemy import case

    rows = await db.execute(
        select(
            SecurityEvent.source_ip,
            func.count().label("event_count"),
            func.sum(case((SecurityEvent.state == EventState.ACTIVE, 1), else_=0)),
            func.sum(case((SecurityEvent.severity == SeverityLevel.HIGH, 1), else_=0)),
            func.max(SecurityEvent.timestamp),
        )
        .group_by(SecurityEvent.source_ip)
        .order_by(desc("event_count"))
        .limit(limit)
    )
    return [
        TopSource(
            source_ip=row[0],
            flow_count=row[1],
            anomaly_count=row[2] or 0,
            high_severity_count=row[3] or 0,
            last_seen=row[4],
        )
        for row in rows
    ]
