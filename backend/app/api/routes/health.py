"""
SecureNet Backend — Health Check Route

Provides system health status for monitoring and diagnostics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.base import get_db
from app.core.config import settings
from app.ml.models import get_ml_models

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.

    Returns the actual status of:
    - Database connection
    - ML model loading
    """

    # Check database connection
    db_status = "connected"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    # Check actual ML model status
    ml_status = "not_loaded"

    try:
        ml_models = get_ml_models()
        ml_status = "loaded" if ml_models.loaded else "not_loaded"
    except Exception:
        ml_status = "not_loaded"

    # Overall application status
    overall_status = (
        "ok"
        if db_status == "connected" and ml_status == "loaded"
        else "degraded"
    )

    return {
        "status": overall_status,
        "database": db_status,
        "ml": ml_status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }