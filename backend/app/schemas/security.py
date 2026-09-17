"""
SecureNet Backend — Security Event Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.security_event import SeverityLevel, EventState, DetectionMode, ActionTaken, Protocol


# ── Contributing Feature ──────────────────────────────────────────────────────

class ContributingFeature(BaseModel):
    """Feature that contributed to anomaly detection"""
    name: str
    value: float | str
    contribution: float


# ── Security Event ────────────────────────────────────────────────────────────

class SecurityEventResponse(BaseModel):
    """Security event data returned to frontend"""
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "by_alias": True,  # This ensures serialization uses aliases
    }
    
    id: str
    timestamp: datetime
    sourceIp: str = Field(..., serialization_alias="sourceIp", validation_alias="source_ip")
    sourcePort: int = Field(..., serialization_alias="sourcePort", validation_alias="source_port")
    destinationIp: str = Field(..., serialization_alias="destinationIp", validation_alias="destination_ip")
    destinationPort: int = Field(..., serialization_alias="destinationPort", validation_alias="destination_port")
    protocol: Protocol
    anomalyScore: float = Field(..., serialization_alias="anomalyScore", validation_alias="anomaly_score")
    severity: SeverityLevel
    attackType: Optional[str] = Field(None, serialization_alias="attackType", validation_alias="attack_type")
    confidence: Optional[float] = None
    mode: DetectionMode
    state: EventState
    actionTaken: ActionTaken = Field(..., serialization_alias="actionTaken", validation_alias="action_taken")
    detectionReason: Optional[str] = Field(None, serialization_alias="detectionReason", validation_alias="detection_reason")
    contributingFeatures: List[ContributingFeature] = Field(default_factory=list, serialization_alias="contributingFeatures", validation_alias="contributing_features")
    flowDurationMs: Optional[int] = Field(None, serialization_alias="flowDurationMs", validation_alias="flow_duration_ms")
    bytesSent: Optional[int] = Field(None, serialization_alias="bytesSent", validation_alias="bytes_sent")
    bytesReceived: Optional[int] = Field(None, serialization_alias="bytesReceived", validation_alias="bytes_received")
    packetsSent: Optional[int] = Field(None, serialization_alias="packetsSent", validation_alias="packets_sent")
    packetsReceived: Optional[int] = Field(None, serialization_alias="packetsReceived", validation_alias="packets_received")


# Removed SecurityEventResponseModel as it's no longer needed


# ── Dashboard Summary ─────────────────────────────────────────────────────────

class AttackTypeCount(BaseModel):
    """Attack type distribution entry"""
    attackType: str
    count: int


class SeverityBreakdown(BaseModel):
    """Event count by severity"""
    low: int
    medium: int
    high: int


class DashboardSummary(BaseModel):
    """Dashboard KPI data"""
    activeFlows: int
    anomaliesLastHour: int
    highSeverityCount: int
    blockedCount: int
    averageAnomalyScore: float
    severityBreakdown: SeverityBreakdown
    attackTypeDistribution: List[AttackTypeCount]
    recentEvents: List[SecurityEventResponse]


# ── Host Status ───────────────────────────────────────────────────────────────

class HostStatus(BaseModel):
    """System resource status"""
    hostname: Optional[str] = None
    os: Optional[str] = None
    cpuPercent: Optional[float] = None
    memoryPercent: Optional[float] = None
    networkInterface: Optional[str] = None
    networkBytesPerSec: Optional[float] = None
    uptime: Optional[int] = None  # seconds
    lastUpdated: Optional[datetime] = None


# ── Protocol Distribution ─────────────────────────────────────────────────────

class ProtocolDistribution(BaseModel):
    """Network protocol statistics"""
    tcp: int
    udp: int
    icmp: int
    other: int
    totalFlows: int


# ── Top Sources ───────────────────────────────────────────────────────────────

class TopSource(BaseModel):
    """Top traffic source statistics"""
    sourceIp: str
    flowCount: int
    anomalyCount: int
    highSeverityCount: int
    lastSeen: datetime
