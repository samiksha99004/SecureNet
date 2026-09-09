"""
SecureNet Backend — Report Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.report import ReportStatus, ReportFormat


# ── Report Filters ────────────────────────────────────────────────────────────

class ReportFilters(BaseModel):
    """Filters applied to report generation"""
    severities: List[str] = []
    states: List[str] = []
    attackTypes: List[str] = []
    includeResolved: bool = True
    includeBreakdown: bool = True


# ── Report Response ───────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    """Generated report metadata"""
    id: str
    name: str
    description: Optional[str] = None
    dateRangeStart: datetime = Field(..., alias="date_range_start")
    dateRangeEnd: datetime = Field(..., alias="date_range_end")
    generatedAt: datetime = Field(..., alias="generated_at")
    status: ReportStatus
    format: ReportFormat
    sizeBytes: Optional[int] = Field(None, alias="size_bytes")
    downloadUrl: Optional[str] = Field(None, alias="download_url")
    filters: ReportFilters
    createdBy: str = Field(..., alias="created_by")
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ── Report Request ────────────────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    """Request to generate a new report"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    dateRangeStart: str = Field(..., description="ISO 8601 date string")
    dateRangeEnd: str = Field(..., description="ISO 8601 date string")
    format: ReportFormat
    filters: ReportFilters


# ── Report Summary ────────────────────────────────────────────────────────────

class ReportSummary(BaseModel):
    """Report statistics"""
    totalReports: int
    recentReportsCount: int  # last 7 days
    generatedThisMonth: int
