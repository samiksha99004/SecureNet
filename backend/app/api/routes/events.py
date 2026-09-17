"""
SecureNet Backend — Security Events Routes

Handles security event queries, filtering, pagination, and state management.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.db.base import get_db
from app.models.user import User
from app.models.security_event import SecurityEvent, EventState, SeverityLevel, Protocol, DetectionMode
from app.schemas.security import SecurityEventResponse, ContributingFeature
from app.schemas.common import PaginatedResponse, MessageResponse
from app.api.dependencies import get_current_user
from app.utils.logger import logger

router = APIRouter(prefix="/events", tags=["Security Events"])


def convert_event_to_response(event: SecurityEvent) -> SecurityEventResponse:
    """Convert SecurityEvent model to response schema with proper camelCase output"""
    contributing_features = []
    if event.contributing_features:
        contributing_features = [
            ContributingFeature(**feat) for feat in event.contributing_features
        ]
    
    # Use model_validate to leverage from_attributes and auto-aliasing
    return SecurityEventResponse.model_validate({
        'id': str(event.id),
        'timestamp': event.timestamp,
        'source_ip': event.source_ip,
        'source_port': event.source_port,
        'destination_ip': event.destination_ip,
        'destination_port': event.destination_port,
        'protocol': event.protocol,
        'anomaly_score': event.anomaly_score,
        'severity': event.severity,
        'attack_type': event.attack_type,
        'confidence': event.confidence,
        'mode': event.mode,
        'state': event.state,
        'action_taken': event.action_taken,
        'detection_reason': event.detection_reason,
        'contributing_features': contributing_features,
        'flow_duration_ms': event.flow_duration_ms,
        'bytes_sent': event.bytes_sent,
        'bytes_received': event.bytes_received,
        'packets_sent': event.packets_sent,
        'packets_received': event.packets_received
    })


@router.get("", response_model=PaginatedResponse[SecurityEventResponse])
async def get_events(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    attackType: Optional[str] = Query(None),
    protocol: Optional[str] = Query(None),
    sortBy: str = Query("timestamp"),
    sortOrder: str = Query("desc", pattern="^(asc|desc)$"),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of security events with filtering and sorting.
    """
    # Build query
    query = select(SecurityEvent)
    conditions = []
    
    # Text search on IPs
    if search:
        conditions.append(
            or_(
                SecurityEvent.source_ip.ilike(f"%{search}%"),
                SecurityEvent.destination_ip.ilike(f"%{search}%")
            )
        )
    
    # Severity filter
    if severity:
        try:
            conditions.append(SecurityEvent.severity == SeverityLevel(severity))
        except ValueError:
            pass
    
    # State filter
    if state:
        try:
            conditions.append(SecurityEvent.state == EventState(state))
        except ValueError:
            pass
    
    # Mode filter
    if mode:
        try:
            conditions.append(SecurityEvent.mode == DetectionMode(mode))
        except ValueError:
            pass
    
    # Attack type filter
    if attackType:
        if attackType.lower() == "normal" or attackType.lower() == "none":
            conditions.append(SecurityEvent.attack_type.is_(None))
        else:
            conditions.append(SecurityEvent.attack_type == attackType)
    
    # Protocol filter
    if protocol:
        try:
            conditions.append(SecurityEvent.protocol == Protocol(protocol))
        except ValueError:
            pass
    
    # Date range filter
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            conditions.append(SecurityEvent.timestamp >= from_dt)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            conditions.append(SecurityEvent.timestamp <= to_dt)
        except ValueError:
            pass
    
    # Apply conditions
    if conditions:
        query = query.where(and_(*conditions))
    
    # Count total
    count_query = select(func.count()).select_from(SecurityEvent)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    result = await db.execute(count_query)
    total = result.scalar()
    
    # Sorting
    sort_column = getattr(SecurityEvent, sortBy, SecurityEvent.timestamp)
    if sortOrder == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Pagination
    offset = (page - 1) * pageSize
    query = query.limit(pageSize).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    events = result.scalars().all()
    
    # Convert to response
    event_responses = [convert_event_to_response(event) for event in events]
    
    total_pages = (total + pageSize - 1) // pageSize
    
    return PaginatedResponse(
        data=event_responses,
        total=total,
        page=page,
        page_size=pageSize,
        total_pages=total_pages
    )


@router.get("/{event_id}", response_model=SecurityEventResponse)
async def get_event_by_id(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a single security event by ID"""
    try:
        event_uuid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID format"
        )
    
    result = await db.execute(
        select(SecurityEvent).where(SecurityEvent.id == event_uuid)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return convert_event_to_response(event)


@router.post("/{event_id}/resolve", response_model=MessageResponse)
async def resolve_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark an event as resolved"""
    try:
        event_uuid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID format"
        )
    
    result = await db.execute(
        select(SecurityEvent).where(SecurityEvent.id == event_uuid)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    event.state = EventState.RESOLVED
    event.resolved_at = datetime.utcnow()
    event.resolved_by = current_user.id
    event.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Event {event_id} resolved by {current_user.email}")
    
    return MessageResponse(message="Event marked as resolved")


@router.post("/{event_id}/false-positive", response_model=MessageResponse)
async def mark_false_positive(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark an event as a false positive"""
    try:
        event_uuid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID format"
        )
    
    result = await db.execute(
        select(SecurityEvent).where(SecurityEvent.id == event_uuid)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    event.state = EventState.FALSE_POSITIVE
    event.resolved_at = datetime.utcnow()
    event.resolved_by = current_user.id
    event.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Event {event_id} marked as false positive by {current_user.email}")
    
    return MessageResponse(message="Event marked as false positive")
