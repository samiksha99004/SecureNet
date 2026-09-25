"""
SecureNet Backend — API Dependencies

Reusable dependencies for FastAPI endpoints: authentication and role checks.
"""

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.base import get_db
from app.models.user import AccountStatus, User, UserRole

# auto_error=False so a missing header yields our own 401 (not a bare 403)
security = HTTPBearer(auto_error=False)


async def user_from_token(token: Optional[str], db: AsyncSession) -> Optional[User]:
    """Resolve an access token to an active user (None if invalid)."""
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (TypeError, ValueError):
        return None
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or user.account_status != AccountStatus.ACTIVE:
        return None
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """The authenticated user for this request (401 otherwise)."""
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles: UserRole):
    """Dependency factory for role-based authorization."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the SecureNet admin can do this.",
            )
        return current_user

    return role_checker


# Two roles: the admin configures SecureNet; every other account is a
# "SecureNet user" (monitor, turn the IDS on/off, alerts, reports). The legacy
# ANALYST / VIEWER values are both treated as SecureNet users.
require_admin = require_role(UserRole.ADMIN)
