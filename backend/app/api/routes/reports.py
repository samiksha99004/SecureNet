"""
SecureNet Backend — Reports Routes

Generates incident reports (CSV / JSON / PDF) from stored security events,
lists them, serves authenticated downloads and deletes them.
"""

import asyncio
import uuid
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.base import get_db
from app.models.report import Report, ReportFormat, ReportStatus
from app.models.security_event import EventState, SecurityEvent, SeverityLevel
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.report import DailyReport, GenerateReportRequest, ReportResponse, ReportSummary
from app.services import exporters, incident_report
from app.utils.logger import logger
from app.utils.timeutil import parse_iso_utc, utcnow

router = APIRouter(prefix="/reports", tags=["Reports"])

MEDIA_TYPES = {
    ReportFormat.CSV: "text/csv",
    ReportFormat.JSON: "application/json",
    ReportFormat.PDF: "application/pdf",
}
MAX_REPORT_EVENTS = 50_000


def _report_path(report: Report) -> Path:
    return settings.reports_dir / f"{report.id}.{report.format.value}"


# ── Daily reports: one per local day that had attacks (built on the fly) ──────

TZ_OFFSET = Query(0, alias="tzOffset", ge=-840, le=840,
                  description="Minutes east of UTC of the viewer's time zone (India = 330)")
DAILY_FORMATS = {"txt": "text/plain; charset=utf-8", "csv": "text/csv", "pdf": "application/pdf"}


@router.get("/daily", response_model=list[DailyReport])
async def list_daily_reports(
    tz_offset: int = TZ_OFFSET,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Days with detected attacks, newest first (empty when nothing has happened)."""
    rows = (await db.execute(
        select(SecurityEvent.timestamp, SecurityEvent.severity, SecurityEvent.attack_type, SecurityEvent.source_ip)
        .order_by(SecurityEvent.timestamp)
    )).all()
    days: dict[date, list] = defaultdict(list)
    for row in rows:
        days[incident_report.to_local(row.timestamp, tz_offset).date()].append(row)

    reports = []
    for day, items in sorted(days.items(), reverse=True):
        severities = [r.severity.value for r in items]
        attacks = [r.attack_type or "Unclassified anomaly" for r in items]
        reports.append(DailyReport(
            date=day.isoformat(),
            total=len(items),
            high=severities.count("high"),
            medium=severities.count("medium"),
            low=severities.count("low"),
            top_attack=max(set(attacks), key=attacks.count),
            sources=len({r.source_ip for r in items}),
            first_seen=items[0].timestamp,
            last_seen=items[-1].timestamp,
        ))
    return reports


@router.get("/daily/{day}/download")
async def download_daily_report(
    day: date,
    format: str = Query("txt", pattern="^(txt|csv|pdf)$"),
    tz_offset: int = TZ_OFFSET,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """That day's report (local time) as .txt, .csv or .pdf."""
    start, end = incident_report.local_day_bounds_utc(day, tz_offset)
    events = (await db.execute(
        select(SecurityEvent).where(SecurityEvent.timestamp >= start, SecurityEvent.timestamp < end)
        .order_by(SecurityEvent.timestamp).limit(MAX_REPORT_EVENTS)
    )).scalars().all()
    if not events:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No attacks were detected on this day.")

    label = day.strftime("%d %b %Y")
    title = f"Daily report - {label}"
    if format == "txt":
        text = await asyncio.to_thread(incident_report.render_text, events, title, tz_offset,
                                       f"{label} 00:00 - 23:59")
        content = text.encode("utf-8")
    elif format == "csv":
        content = await asyncio.to_thread(exporters.to_csv, events)
    else:
        content = await asyncio.to_thread(exporters.to_pdf, events, f"SecureNet {title}",
                                          f"{len(events)} attack(s) - times in UTC")
    filename = incident_report.report_filename("daily-report", day.isoformat(), format)
    return Response(content=content, media_type=DAILY_FORMATS[format],
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/summary", response_model=ReportSummary)
async def get_report_summary(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    now = utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async def count(*conds):
        q = select(func.count()).select_from(Report)
        if conds:
            q = q.where(*conds)
        return (await db.execute(q)).scalar() or 0

    return ReportSummary(
        total_reports=await count(),
        recent_reports_count=await count(Report.generated_at >= now - timedelta(days=7)),
        generated_this_month=await count(Report.generated_at >= month_start),
    )


@router.get("", response_model=PaginatedResponse[ReportResponse])
async def get_reports(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(Report))).scalar() or 0
    reports = (await db.execute(
        select(Report).order_by(Report.generated_at.desc()).limit(pageSize).offset((page - 1) * pageSize)
    )).scalars().all()
    return PaginatedResponse[ReportResponse](
        data=[ReportResponse.model_validate(r) for r in reports],
        total=total,
        page=page,
        page_size=pageSize,
        total_pages=(total + pageSize - 1) // pageSize,
    )


@router.post("", response_model=ReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a report for the given date range and filters."""
    try:
        start = parse_iso_utc(request.date_range_start)
        end = parse_iso_utc(request.date_range_end)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use ISO 8601.")
    if start is None or end is None or start >= end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date must be before end date")

    filters = request.filters
    report = Report(
        name=request.name,
        description=request.description,
        date_range_start=start,
        date_range_end=end,
        format=request.format,
        filters=filters.model_dump(by_alias=True),
        created_by=current_user.id,
        status=ReportStatus.GENERATING,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    try:
        query = select(SecurityEvent).where(SecurityEvent.timestamp >= start, SecurityEvent.timestamp <= end)
        if filters.severities:
            query = query.where(SecurityEvent.severity.in_([SeverityLevel(s) for s in filters.severities]))
        if filters.states:
            query = query.where(SecurityEvent.state.in_([EventState(s) for s in filters.states]))
        if filters.attack_types:
            query = query.where(SecurityEvent.attack_type.in_(filters.attack_types))
        if not filters.include_resolved:
            query = query.where(SecurityEvent.state.notin_([EventState.RESOLVED, EventState.FALSE_POSITIVE]))
        events = (await db.execute(
            query.order_by(SecurityEvent.timestamp.desc()).limit(MAX_REPORT_EVENTS)
        )).scalars().all()

        meta = {
            "name": report.name,
            "description": report.description,
            "from": request.date_range_start,
            "to": request.date_range_end,
            "generatedBy": current_user.email,
            "filters": report.filters,
        }
        if report.format == ReportFormat.CSV:
            body = await asyncio.to_thread(exporters.to_csv, events)
        elif report.format == ReportFormat.JSON:
            body = await asyncio.to_thread(exporters.to_json, events, meta, filters.include_breakdown)
        else:
            subtitle = f"{start:%Y-%m-%d %H:%M} → {end:%Y-%m-%d %H:%M} UTC · generated by {current_user.email}"
            body = await asyncio.to_thread(exporters.to_pdf, events, report.name, subtitle, filters.include_breakdown)

        path = _report_path(report)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, body)

        report.status = ReportStatus.READY
        report.size_bytes = len(body)
        report.download_url = f"/api/reports/{report.id}/download"
        report.generated_at = utcnow()
    except ValueError as exc:  # bad severity/state value in filters
        report.status = ReportStatus.FAILED
        report.error_message = f"Invalid filter: {exc}"
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}", exc_info=True)
        report.status = ReportStatus.FAILED
        report.error_message = str(exc)

    await db.commit()
    await db.refresh(report)
    logger.info(f"Report '{report.name}' {report.status.value} for {current_user.email}")
    return ReportResponse.model_validate(report)


async def _load_report(db: AsyncSession, report_id: str) -> Report:
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report ID format")
    report = (await db.execute(select(Report).where(Report.id == report_uuid))).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _load_report(db, report_id)
    path = _report_path(report)
    if report.status != ReportStatus.READY or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file is not available")
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in report.name).strip() or "report"
    return FileResponse(path, media_type=MEDIA_TYPES[report.format], filename=f"{safe_name}.{report.format.value}")


@router.delete("/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _load_report(db, report_id)
    if report.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You don't have permission to delete this report")
    path = _report_path(report)
    await db.delete(report)
    await db.commit()
    path.unlink(missing_ok=True)
    logger.info(f"Report deleted by {current_user.email}: {report.name}")
    return MessageResponse(message="Report deleted successfully")
