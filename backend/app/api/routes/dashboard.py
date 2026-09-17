"""
SecureNet Backend — Dashboard Routes

Provides summary statistics, protocol distribution, and top sources
for the dashboard view. Implements simple caching for performance.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import time

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

# Configure router to use aliases in responses (camelCase)
router.response_model_by_alias = True

# Simple cache for dashboard summary (30 second TTL)
_summary_cache: Optional[DashboardSummary] = None
_summary_cache_time: float = 0
CACHE_TTL = 30  # seconds


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard summary with KPIs and recent events.
    Returns actual data from the database ONLY when IDS is enabled.
    When IDS is OFF, returns zeros/empty data.
    Cached for 30 seconds for performance.
    Returns camelCase JSON.
    """
    from app.ml.ids_service_ensemble import get_ids_service
    
    global _summary_cache, _summary_cache_time
    
    # Check if IDS is enabled
    ids = get_ids_service()
    if not ids.is_enabled():
        # Return empty summary when IDS is OFF
        empty_summary = DashboardSummary(
            activeFlows=0,
            anomaliesLastHour=0,
            highSeverityCount=0,
            blockedCount=0,
            averageAnomalyScore=0.0,
            severityBreakdown=SeverityBreakdown(low=0, medium=0, high=0),
            attackTypeDistribution=[],
            recentEvents=[]
        )
        return JSONResponse(content=jsonable_encoder(empty_summary.model_dump(by_alias=True)))
    
    # Check cache (only when IDS is ON)
    current_time = time.time()
    if _summary_cache and (current_time - _summary_cache_time) < CACHE_TTL:
        return JSONResponse(content=jsonable_encoder(_summary_cache.model_dump(by_alias=True)))
    
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
    
    summary = DashboardSummary(
        activeFlows=active_flows,
        anomaliesLastHour=anomalies_last_hour,
        highSeverityCount=high_severity_count,
        blockedCount=blocked_count,
        averageAnomalyScore=round(avg_score, 4),
        severityBreakdown=severity_breakdown,
        attackTypeDistribution=attack_distribution,
        recentEvents=recent_events
    )
    
    # Update cache
    _summary_cache = summary
    _summary_cache_time = current_time
    
    # Return with camelCase field names
    return JSONResponse(content=jsonable_encoder(summary.model_dump(by_alias=True)))


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
    from sqlalchemy import case
    
    # Aggregate by source IP
    result = await db.execute(
        select(
            SecurityEvent.source_ip,
            func.count().label('flow_count'),
            func.sum(
                case((SecurityEvent.anomaly_score > 0.5, 1), else_=0)
            ).label('anomaly_count'),
            func.sum(
                case((SecurityEvent.severity == SeverityLevel.HIGH, 1), else_=0)
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
