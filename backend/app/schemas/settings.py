"""
SecureNet Backend — Settings Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

from app.models.settings import DetectionSensitivity, ProtectionMode, WhitelistEntryType


# ── Detection Settings ────────────────────────────────────────────────────────

class DetectionSettingsResponse(BaseModel):
    """Detection configuration"""
    enabled: bool
    sensitivity: DetectionSensitivity
    anomalyThreshold: float = Field(..., alias="anomaly_threshold")
    minFlowsForAnalysis: int = Field(..., alias="min_flows_for_analysis")
    analysisIntervalMs: int = Field(..., alias="analysis_interval_ms")
    stage2Enabled: bool = Field(..., alias="stage2_enabled")
    stage2ConfidenceThreshold: float = Field(..., alias="stage2_confidence_threshold")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class DetectionSettingsUpdate(BaseModel):
    """Update detection settings"""
    enabled: Optional[bool] = None
    sensitivity: Optional[DetectionSensitivity] = None
    anomalyThreshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    minFlowsForAnalysis: Optional[int] = Field(None, ge=1)
    analysisIntervalMs: Optional[int] = Field(None, ge=100)
    stage2Enabled: Optional[bool] = None
    stage2ConfidenceThreshold: Optional[float] = Field(None, ge=0.0, le=1.0)


# ── Protection Settings ───────────────────────────────────────────────────────

class ProtectionSettingsResponse(BaseModel):
    """Protection configuration"""
    mode: ProtectionMode
    autoBlock: bool = Field(..., alias="auto_block")
    autoBlockSeverities: List[str] = Field(..., alias="auto_block_severities")
    blockDurationSeconds: int = Field(..., alias="block_duration_seconds")
    maxBlockedIps: int = Field(..., alias="max_blocked_ips")
    notifyOnBlock: bool = Field(..., alias="notify_on_block")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class ProtectionSettingsUpdate(BaseModel):
    """Update protection settings"""
    mode: Optional[ProtectionMode] = None
    autoBlock: Optional[bool] = None
    autoBlockSeverities: Optional[List[str]] = None
    blockDurationSeconds: Optional[int] = Field(None, ge=1)
    maxBlockedIps: Optional[int] = Field(None, ge=1)
    notifyOnBlock: Optional[bool] = None


# ── Notification Settings ─────────────────────────────────────────────────────

class NotificationSettingsResponse(BaseModel):
    """Notification configuration"""
    emailEnabled: bool = Field(..., alias="email_enabled")
    emailAddress: Optional[str] = Field(None, alias="email_address")
    alertOnHigh: bool = Field(..., alias="alert_on_high")
    alertOnMedium: bool = Field(..., alias="alert_on_medium")
    alertOnBlock: bool = Field(..., alias="alert_on_block")
    digestEnabled: bool = Field(..., alias="digest_enabled")
    digestIntervalHours: int = Field(..., alias="digest_interval_hours")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class NotificationSettingsUpdate(BaseModel):
    """Update notification settings"""
    emailEnabled: Optional[bool] = None
    emailAddress: Optional[EmailStr] = None
    alertOnHigh: Optional[bool] = None
    alertOnMedium: Optional[bool] = None
    alertOnBlock: Optional[bool] = None
    digestEnabled: Optional[bool] = None
    digestIntervalHours: Optional[int] = Field(None, ge=1)


# ── System Settings ───────────────────────────────────────────────────────────

class SystemSettingsResponse(BaseModel):
    """System configuration"""
    logRetentionDays: int = Field(..., alias="log_retention_days")
    maxStoredEvents: int = Field(..., alias="max_stored_events")
    timezone: str
    dateFormat: str = Field(..., alias="date_format")
    debugMode: bool = Field(..., alias="debug_mode")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class SystemSettingsUpdate(BaseModel):
    """Update system settings"""
    logRetentionDays: Optional[int] = Field(None, ge=1)
    maxStoredEvents: Optional[int] = Field(None, ge=100)
    timezone: Optional[str] = None
    dateFormat: Optional[str] = None
    debugMode: Optional[bool] = None


# ── All Settings ──────────────────────────────────────────────────────────────

class AllSettingsResponse(BaseModel):
    """Combined settings response"""
    detection: DetectionSettingsResponse
    protection: ProtectionSettingsResponse
    notifications: NotificationSettingsResponse
    system: SystemSettingsResponse


# ── Whitelist Entry ───────────────────────────────────────────────────────────

class WhitelistEntryResponse(BaseModel):
    """Whitelist entry"""
    id: str
    type: WhitelistEntryType
    value: str
    description: Optional[str] = None
    createdAt: datetime = Field(..., alias="created_at")
    createdBy: Optional[str] = Field(None, alias="created_by")
    active: bool
    
    class Config:
        from_attributes = True
        populate_by_name = True


class CreateWhitelistEntryRequest(BaseModel):
    """Create whitelist entry"""
    type: WhitelistEntryType
    value: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
