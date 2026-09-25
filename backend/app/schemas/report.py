"""
SecureNet Backend — Report Schemas
"""

from typing import Optional, List

from pydantic import Field

from app.models.report import ReportStatus, ReportFormat
from app.schemas.base import CamelModel, IdStr, UtcDatetime


class ReportFilters(CamelModel):
    """Filters applied to report generation"""
    severities: List[str] = []
    states: List[str] = []
    attack_types: List[str] = []
    include_resolved: bool = True
    include_breakdown: bool = True


class ReportResponse(CamelModel):
    """Generated report metadata"""
    id: IdStr
    name: str
    description: Optional[str] = None
    date_range_start: UtcDatetime
    date_range_end: UtcDatetime
    generated_at: UtcDatetime
    status: ReportStatus
    format: ReportFormat
    size_bytes: Optional[int] = None
    download_url: Optional[str] = None
    filters: ReportFilters
    created_by: IdStr
    error_message: Optional[str] = None


class GenerateReportRequest(CamelModel):
    """Request to generate a new report"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    date_range_start: str = Field(..., description="ISO 8601 date string")
    date_range_end: str = Field(..., description="ISO 8601 date string")
    format: ReportFormat
    filters: ReportFilters = ReportFilters()


class ReportSummary(CamelModel):
    """Report statistics"""
    total_reports: int
    recent_reports_count: int  # last 7 days
    generated_this_month: int


class DailyReport(CamelModel):
    """One day (local time) that had detected attacks — shown as a box on the Reports page."""
    date: str                    # YYYY-MM-DD, local calendar day
    total: int
    high: int
    medium: int
    low: int
    top_attack: Optional[str] = None
    sources: int
    first_seen: UtcDatetime
    last_seen: UtcDatetime
