"""
SecureNet Backend — Health Check Route

Provides system health status for monitoring and diagnostics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.base import get_db
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    Returns status of database and system components.
    """
    
    # Check database connection
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    
    # Check ML models (would need actual model loading logic)
    ml_status = "not_loaded"  # TODO: Check actual model status
    
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "ml": ml_status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }
