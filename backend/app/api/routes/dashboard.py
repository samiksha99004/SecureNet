"""
SecureNet Backend — Dashboard Routes

Provides summary statistics, protocol distribution, and top sources
for the dashboard view.
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.db.base import get_db
from app.models.user import User
from app.models.security_event import SecurityEvent, SeverityLevel, EventState, Protocol, ActionTaken
from app.schemas.security import (
    DashboardSummary,
    HostStatus,
    ProtocolDistribution,
    TopSource,
    SecurityEventResponse,
    AttackTypeCount,
    SeverityBreakdown
)
from app.api.dependencies import get_current_user
from app.api.routes.events import convert_event_to_response
import platform
import psutil

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard summary with KPIs and recent events.
    Returns actual data from the database.
    """
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    # Active flows (events in last hour)
    result = await db.execute(
        select(func.count())
        .select_from(SecurityEvent)
        .where(SecurityEvent.timestamp >= one_hour_ago)
    )
    active_flows = result.scalar() or 0
    
    # Anomalies in last hour
    result = await db.execute(
        select(func.count())
        .select_from(SecurityEvent)
        .where(
            and_(
                SecurityEvent.timestamp >= one_hour_ago,
                SecurityEvent.anomaly_score > 0.5
            )
        )
    )
    anomalies_last_hour = result.scalar() or 0
    
    # High severity count
    result = await db.execute(
        select(func.count())
        .select_from(SecurityEvent)
        .where(
            and_(
                SecurityEvent.severity == SeverityLevel.HIGH,
                SecurityEvent.state == EventState.ACTIVE
            )
        )
    )
    high_severity_count = result.scalar() or 0
    
    # Blocked count
    result = await db.execute(
        select(func.count())
        .select_from(SecurityEvent)
        .where(SecurityEvent.action_taken == ActionTaken.BLOCKED)
    )
    blocked_count = result.scalar() or 0
    
    # Average anomaly score
    result = await db.execute(
        select(func.avg(SecurityEvent.anomaly_score))
        .select_from(SecurityEvent)
        .where(SecurityEvent.timestamp >= one_hour_ago)
    )
    avg_score = result.scalar() or 0.0
    
    # Severity breakdown
    result = await db.execute(
        select(SecurityEvent.severity, func.count())
        .where(SecurityEvent.state == EventState.ACTIVE)
        .group_by(SecurityEvent.severity)
    )
    severity_counts = {row[0]: row[1] for row in result}
    
    severity_breakdown = SeverityBreakdown(
        low=severity_counts.get(SeverityLevel.LOW, 0),
        medium=severity_counts.get(SeverityLevel.MEDIUM, 0),
        high=severity_counts.get(SeverityLevel.HIGH, 0)
    )
    
    # Attack type distribution
    result = await db.execute(
        select(SecurityEvent.attack_type, func.count())
        .where(SecurityEvent.attack_type.isnot(None))
        .group_by(SecurityEvent.attack_type)
        .order_by(desc(func.count()))
        .limit(10)
    )
    attack_distribution = [
        AttackTypeCount(attackType=row[0], count=row[1])
        for row in result
    ]
    
    # Recent events (last 10)
    result = await db.execute(
        select(SecurityEvent)
        .order_by(desc(SecurityEvent.timestamp))
        .limit(10)
    )
    recent_events_models = result.scalars().all()
    recent_events = [convert_event_to_response(event) for event in recent_events_models]
    
    return DashboardSummary(
        activeFlows=active_flows,
        anomaliesLastHour=anomalies_last_hour,
        highSeverityCount=high_severity_count,
        blockedCount=blocked_count,
        averageAnomalyScore=round(avg_score, 4),
        severityBreakdown=severity_breakdown,
        attackTypeDistribution=attack_distribution,
        recentEvents=recent_events
    )


@router.get("/host-status", response_model=HostStatus)
async def get_host_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current host system resource status.
    Returns actual system metrics.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Network stats
        net_io = psutil.net_io_counters()
        network_bytes_per_sec = None  # Would need historical tracking
        
        # Uptime
        boot_time = psutil.boot_time()
        uptime = int(datetime.now().timestamp() - boot_time)
        
        return HostStatus(
            hostname=platform.node(),
            os=f"{platform.system()} {platform.release()}",
            cpuPercent=round(cpu_percent, 2),
            memoryPercent=round(memory_percent, 2),
            networkInterface=None,  # Could be enhanced
            networkBytesPerSec=network_bytes_per_sec,
            uptime=uptime,
            lastUpdated=datetime.utcnow()
        )
    except Exception:
        # Return null values if system metrics unavailable
        return HostStatus()


@router.get("/protocol-distribution", response_model=ProtocolDistribution)
async def get_protocol_distribution(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get network protocol distribution from recent events.
    Returns actual data from database.
    """
    result = await db.execute(
        select(SecurityEvent.protocol, func.count())
        .group_by(SecurityEvent.protocol)
    )
    protocol_counts = {row[0]: row[1] for row in result}
    
    tcp_count = protocol_counts.get(Protocol.TCP, 0)
    udp_count = protocol_counts.get(Protocol.UDP, 0)
    icmp_count = protocol_counts.get(Protocol.ICMP, 0)
    other_count = protocol_counts.get(Protocol.OTHER, 0)
    
    total = tcp_count + udp_count + icmp_count + other_count
    
    return ProtocolDistribution(
        tcp=tcp_count,
        udp=udp_count,
        icmp=icmp_count,
        other=other_count,
        totalFlows=total
    )


@router.get("/top-sources", response_model=List[TopSource])
async def get_top_sources(
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top source IPs by event count.
    Returns actual data from database.
    """
    # Aggregate by source IP
    result = await db.execute(
        select(
            SecurityEvent.source_ip,
            func.count().label('flow_count'),
            func.sum(
                func.cast(SecurityEvent.anomaly_score > 0.5, func.Integer())
            ).label('anomaly_count'),
            func.sum(
                func.cast(SecurityEvent.severity == SeverityLevel.HIGH, func.Integer())
            ).label('high_severity_count'),
            func.max(SecurityEvent.timestamp).label('last_seen')
        )
        .group_by(SecurityEvent.source_ip)
        .order_by(desc('flow_count'))
        .limit(limit)
    )
    
    top_sources = []
    for row in result:
        top_sources.append(
            TopSource(
                sourceIp=row[0],
                flowCount=row[1],
                anomalyCount=row[2] or 0,
                highSeverityCount=row[3] or 0,
                lastSeen=row[4]
            )
        )
    
    return top_sources
