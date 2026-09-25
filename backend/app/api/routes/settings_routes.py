"""
SecureNet Backend — Settings Routes

Detection, protection, notification and system settings plus the whitelist.
Anyone signed in can read settings; only the admin can change them.
Every change is pushed to the running IDS immediately.
"""

from typing import Type, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.dependencies import get_current_user, require_admin
from app.db.base import get_db
from app.ml.ids_service import get_ids_service
from app.models.settings import (
    DetectionSettings,
    NotificationSettings,
    ProtectionSettings,
    SystemSettings,
    WhitelistEntry,
)
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.settings import (
    AllSettingsResponse,
    CreateWhitelistEntryRequest,
    DetectionSettingsResponse,
    DetectionSettingsUpdate,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    ProtectionSettingsResponse,
    ProtectionSettingsUpdate,
    SystemSettingsResponse,
    SystemSettingsUpdate,
    WhitelistEntryResponse,
)
from app.utils.logger import logger
from app.utils.timeutil import utcnow

router = APIRouter(prefix="/settings", tags=["Settings"])

M = TypeVar("M")


async def get_or_create(db: AsyncSession, model: Type[M]) -> M:
    """Fetch the single settings row, creating it with defaults if missing."""
    row = (await db.execute(select(model).order_by(model.updated_at).limit(1))).scalars().first()
    if row is None:
        row = model()
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def _apply_update(db: AsyncSession, model, updates, user: User):
    row = await get_or_create(db, model)
    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is None and not model.__table__.columns[field].nullable:
            continue
        setattr(row, field, value)
    row.updated_at = utcnow()
    row.updated_by = user.id
    await db.commit()
    await db.refresh(row)
    await get_ids_service().reload_config()
    logger.info(f"{model.__tablename__} updated by {user.email}")
    return row


@router.get("", response_model=AllSettingsResponse)
async def get_all_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return AllSettingsResponse(
        detection=DetectionSettingsResponse.model_validate(await get_or_create(db, DetectionSettings)),
        protection=ProtectionSettingsResponse.model_validate(await get_or_create(db, ProtectionSettings)),
        notifications=NotificationSettingsResponse.model_validate(await get_or_create(db, NotificationSettings)),
        system=SystemSettingsResponse.model_validate(await get_or_create(db, SystemSettings)),
    )


@router.get("/detection", response_model=DetectionSettingsResponse)
async def get_detection_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return DetectionSettingsResponse.model_validate(await get_or_create(db, DetectionSettings))


@router.put("/detection", response_model=DetectionSettingsResponse)
async def update_detection_settings(
    updates: DetectionSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return DetectionSettingsResponse.model_validate(await _apply_update(db, DetectionSettings, updates, current_user))


@router.get("/protection", response_model=ProtectionSettingsResponse)
async def get_protection_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ProtectionSettingsResponse.model_validate(await get_or_create(db, ProtectionSettings))


@router.put("/protection", response_model=ProtectionSettingsResponse)
async def update_protection_settings(
    updates: ProtectionSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await _apply_update(db, ProtectionSettings, updates, current_user)
    ids = get_ids_service()
    if updates.mode is not None and ids.enabled:
        await ids.set_mode(updates.mode.value)
        await ids.broadcast_status()
    return ProtectionSettingsResponse.model_validate(row)


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return NotificationSettingsResponse.model_validate(await get_or_create(db, NotificationSettings))


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    updates: NotificationSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return NotificationSettingsResponse.model_validate(
        await _apply_update(db, NotificationSettings, updates, current_user)
    )


@router.get("/system", response_model=SystemSettingsResponse)
async def get_system_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return SystemSettingsResponse.model_validate(await get_or_create(db, SystemSettings))


@router.put("/system", response_model=SystemSettingsResponse)
async def update_system_settings(
    updates: SystemSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return SystemSettingsResponse.model_validate(await _apply_update(db, SystemSettings, updates, current_user))


# ── Whitelist Management ──────────────────────────────────────────────────────

@router.get("/whitelist", response_model=list[WhitelistEntryResponse])
async def get_whitelist(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WhitelistEntry).where(WhitelistEntry.active.is_(True)).order_by(WhitelistEntry.created_at.desc())
    )
    return [WhitelistEntryResponse.model_validate(entry) for entry in result.scalars().all()]


@router.post("/whitelist", response_model=WhitelistEntryResponse)
async def add_whitelist_entry(
    request: CreateWhitelistEntryRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        select(WhitelistEntry).where(
            WhitelistEntry.type == request.type,
            WhitelistEntry.value == request.value,
            WhitelistEntry.active.is_(True),
        ).limit(1)
    )).scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This whitelist entry already exists")

    entry = WhitelistEntry(
        type=request.type,
        value=request.value,
        description=request.description,
        created_by=current_user.id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    await get_ids_service().reload_config()
    logger.info(f"Whitelist entry added by {current_user.email}: {request.type.value}:{request.value}")
    return WhitelistEntryResponse.model_validate(entry)


@router.delete("/whitelist/{entry_id}", response_model=MessageResponse)
async def remove_whitelist_entry(
    entry_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        entry_uuid = uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entry ID format")

    entry = (await db.execute(select(WhitelistEntry).where(WhitelistEntry.id == entry_uuid))).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Whitelist entry not found")

    entry.active = False  # soft delete (keeps the audit trail)
    await db.commit()
    await get_ids_service().reload_config()
    logger.info(f"Whitelist entry removed by {current_user.email}: {entry.type.value}:{entry.value}")
    return MessageResponse(message="Whitelist entry removed successfully")
