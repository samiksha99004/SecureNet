"""
SecureNet Backend — Settings Routes

Handles all application settings: detection, protection, notifications,
system configuration, and whitelist management.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.base import get_db
from app.models.user import User
from app.models.settings import (
    DetectionSettings,
    ProtectionSettings,
    NotificationSettings,
    SystemSettings,
    WhitelistEntry
)
from app.schemas.settings import (
    DetectionSettingsResponse,
    DetectionSettingsUpdate,
    ProtectionSettingsResponse,
    ProtectionSettingsUpdate,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    SystemSettingsResponse,
    SystemSettingsUpdate,
    AllSettingsResponse,
    WhitelistEntryResponse,
    CreateWhitelistEntryRequest
)
from app.schemas.common import MessageResponse
from app.api.dependencies import get_current_user
from app.utils.logger import logger

router = APIRouter(prefix="/settings", tags=["Settings"])


async def get_or_create_detection_settings(db: AsyncSession) -> DetectionSettings:
    """Get or create detection settings (singleton)"""
    result = await db.execute(select(DetectionSettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = DetectionSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


async def get_or_create_protection_settings(db: AsyncSession) -> ProtectionSettings:
    """Get or create protection settings (singleton)"""
    result = await db.execute(select(ProtectionSettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = ProtectionSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


async def get_or_create_notification_settings(db: AsyncSession) -> NotificationSettings:
    """Get or create notification settings (singleton)"""
    result = await db.execute(select(NotificationSettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = NotificationSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


async def get_or_create_system_settings(db: AsyncSession) -> SystemSettings:
    """Get or create system settings (singleton)"""
    result = await db.execute(select(SystemSettings))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = SystemSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


@router.get("", response_model=AllSettingsResponse)
async def get_all_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all settings categories"""
    detection = await get_or_create_detection_settings(db)
    protection = await get_or_create_protection_settings(db)
    notifications = await get_or_create_notification_settings(db)
    system = await get_or_create_system_settings(db)
    
    return AllSettingsResponse(
        detection=DetectionSettingsResponse.model_validate(detection),
        protection=ProtectionSettingsResponse.model_validate(protection),
        notifications=NotificationSettingsResponse.model_validate(notifications),
        system=SystemSettingsResponse.model_validate(system)
    )


@router.get("/detection", response_model=DetectionSettingsResponse)
async def get_detection_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detection settings"""
    settings = await get_or_create_detection_settings(db)
    return DetectionSettingsResponse.model_validate(settings)


@router.put("/detection", response_model=DetectionSettingsResponse)
async def update_detection_settings(
    updates: DetectionSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update detection settings"""
    settings = await get_or_create_detection_settings(db)
    
    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_at = datetime.utcnow()
    settings.updated_by = current_user.id
    
    await db.commit()
    await db.refresh(settings)
    
    logger.info(f"Detection settings updated by {current_user.email}")
    
    return DetectionSettingsResponse.model_validate(settings)


@router.get("/protection", response_model=ProtectionSettingsResponse)
async def get_protection_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get protection settings"""
    settings = await get_or_create_protection_settings(db)
    return ProtectionSettingsResponse.model_validate(settings)


@router.put("/protection", response_model=ProtectionSettingsResponse)
async def update_protection_settings(
    updates: ProtectionSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update protection settings"""
    settings = await get_or_create_protection_settings(db)
    
    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_at = datetime.utcnow()
    settings.updated_by = current_user.id
    
    await db.commit()
    await db.refresh(settings)
    
    logger.info(f"Protection settings updated by {current_user.email}")
    
    return ProtectionSettingsResponse.model_validate(settings)


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification settings"""
    settings = await get_or_create_notification_settings(db)
    return NotificationSettingsResponse.model_validate(settings)


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    updates: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update notification settings"""
    settings = await get_or_create_notification_settings(db)
    
    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_at = datetime.utcnow()
    settings.updated_by = current_user.id
    
    await db.commit()
    await db.refresh(settings)
    
    logger.info(f"Notification settings updated by {current_user.email}")
    
    return NotificationSettingsResponse.model_validate(settings)


@router.get("/system", response_model=SystemSettingsResponse)
async def get_system_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system settings"""
    settings = await get_or_create_system_settings(db)
    return SystemSettingsResponse.model_validate(settings)


@router.put("/system", response_model=SystemSettingsResponse)
async def update_system_settings(
    updates: SystemSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update system settings"""
    settings = await get_or_create_system_settings(db)
    
    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_at = datetime.utcnow()
    settings.updated_by = current_user.id
    
    await db.commit()
    await db.refresh(settings)
    
    logger.info(f"System settings updated by {current_user.email}")
    
    return SystemSettingsResponse.model_validate(settings)


# ── Whitelist Management ──────────────────────────────────────────────────────

@router.get("/whitelist", response_model=list[WhitelistEntryResponse])
async def get_whitelist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all whitelist entries"""
    result = await db.execute(
        select(WhitelistEntry).where(WhitelistEntry.active == True).order_by(WhitelistEntry.created_at.desc())
    )
    entries = result.scalars().all()
    
    return [WhitelistEntryResponse.model_validate(entry) for entry in entries]


@router.post("/whitelist", response_model=WhitelistEntryResponse)
async def add_whitelist_entry(
    request: CreateWhitelistEntryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new whitelist entry"""
    
    # Check for duplicates
    result = await db.execute(
        select(WhitelistEntry).where(
            WhitelistEntry.type == request.type,
            WhitelistEntry.value == request.value,
            WhitelistEntry.active == True
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This whitelist entry already exists"
        )
    
    entry = WhitelistEntry(
        type=request.type,
        value=request.value,
        description=request.description,
        created_by=current_user.id
    )
    
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    logger.info(f"Whitelist entry added by {current_user.email}: {request.type}:{request.value}")
    
    return WhitelistEntryResponse.model_validate(entry)


@router.delete("/whitelist/{entry_id}", response_model=MessageResponse)
async def remove_whitelist_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a whitelist entry"""
    try:
        entry_uuid = UUID(entry_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entry ID format"
        )
    
    result = await db.execute(
        select(WhitelistEntry).where(WhitelistEntry.id == entry_uuid)
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Whitelist entry not found"
        )
    
    # Soft delete
    entry.active = False
    await db.commit()
    
    logger.info(f"Whitelist entry removed by {current_user.email}: {entry.type}:{entry.value}")
    
    return MessageResponse(message="Whitelist entry removed successfully")
