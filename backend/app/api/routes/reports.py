"""
SecureNet Backend — Reports Routes

Handles report generation, listing, and download.
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from uuid import UUID

from app.db.base import get_db
from app.models.user import User
from app.models.report import Report, ReportStatus
from app.schemas.report import ReportResponse, GenerateReportRequest, ReportSummary
from app.schemas.common import PaginatedResponse, MessageResponse
from app.api.dependencies import get_current_user
from app.utils.logger import logger

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary", response_model=ReportSummary)
async def get_report_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get report statistics"""
    
    # Total reports
    result = await db.execute(select(func.count()).select_from(Report))
    total_reports = result.scalar() or 0
    
    # Recent reports (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(func.count())
        .select_from(Report)
        .where(Report.generated_at >= seven_days_ago)
    )
    recent_reports_count = result.scalar() or 0
    
    # Generated this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count())
        .select_from(Report)
        .where(Report.generated_at >= month_start)
    )
    generated_this_month = result.scalar() or 0
    
    return ReportSummary(
        totalReports=total_reports,
        recentReportsCount=recent_reports_count,
        generatedThisMonth=generated_this_month
    )


@router.get("", response_model=PaginatedResponse[ReportResponse])
async def get_reports(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of reports"""
    
    # Count total
    result = await db.execute(select(func.count()).select_from(Report))
    total = result.scalar()
    
    # Get reports
    offset = (page - 1) * pageSize
    result = await db.execute(
        select(Report)
        .order_by(Report.generated_at.desc())
        .limit(pageSize)
        .offset(offset)
    )
    reports = result.scalars().all()
    
    # Convert to response
    report_responses = [ReportResponse.model_validate(report) for report in reports]
    
    total_pages = (total + pageSize - 1) // pageSize
    
    return PaginatedResponse(
        data=report_responses,
        total=total,
        page=page,
        page_size=pageSize,
        total_pages=total_pages
    )


@router.post("", response_model=ReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new security report.
    Report generation happens asynchronously in the background.
    """
    
    # Parse dates
    try:
        date_range_start = datetime.fromisoformat(request.dateRangeStart.replace('Z', '+00:00'))
        date_range_end = datetime.fromisoformat(request.dateRangeEnd.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO 8601 format."
        )
    
    # Validate date range
    if date_range_start >= date_range_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    # Create report
    report = Report(
        name=request.name,
        description=request.description,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        format=request.format,
        filters=request.filters.model_dump(),
        created_by=current_user.id,
        status=ReportStatus.PENDING
    )
    
    db.add(report)
    await db.commit()
    await db.refresh(report)
    
    # TODO: Trigger background task for actual report generation
    logger.info(f"Report generation requested by {current_user.email}: {report.name}")
    
    return ReportResponse.model_validate(report)


@router.delete("/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a report"""
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report ID format"
        )
    
    result = await db.execute(
        select(Report).where(Report.id == report_uuid)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Check ownership or admin
    if report.created_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this report"
        )
    
    await db.delete(report)
    await db.commit()
    
    logger.info(f"Report deleted by {current_user.email}: {report.name}")
    
    return MessageResponse(message="Report deleted successfully")
