"""Pydantic schemas for request/response validation"""

from app.schemas.auth import *
from app.schemas.security import *
from app.schemas.settings import *
from app.schemas.common import *
from app.schemas.model import *
from app.schemas.report import *

__all__ = [
    # Auth
    "UserResponse",
    "LoginRequest",
    "SignupRequest",
    "OtpVerifyRequest",
    "OtpResendRequest",
    "ChangePasswordRequest",
    "AuthTokens",
    "AuthResponse",
    "OtpVerifyResponse",
    # Security
    "SecurityEventResponse",
    "DashboardSummary",
    "HostStatus",
    "ProtocolDistribution",
    "TopSource",
    # Settings
    "DetectionSettingsResponse",
    "DetectionSettingsUpdate",
    "ProtectionSettingsResponse",
    "ProtectionSettingsUpdate",
    "NotificationSettingsResponse",
    "NotificationSettingsUpdate",
    "SystemSettingsResponse",
    "SystemSettingsUpdate",
    "AllSettingsResponse",
    "WhitelistEntryResponse",
    "CreateWhitelistEntryRequest",
    # Common
    "PaginatedResponse",
    "MessageResponse",
    "ApiError",
    # Model
    "ModelInfo",
    "FeatureImportance",
    # Report
    "ReportResponse",
    "GenerateReportRequest",
    "ReportSummary",
]
