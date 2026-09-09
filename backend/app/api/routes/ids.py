"""
SecureNet Backend — IDS Control Routes

Single IDS ON/OFF control with status monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models.user import User, UserRole
from app.api.dependencies import get_current_user, require_role
from app.ml.ids_service import get_ids_service
from app.utils.logger import logger

router = APIRouter(prefix="/ids", tags=["IDS Control"])


class IDSStatusResponse(BaseModel):
    """IDS status information"""
    enabled: bool
    mode: str
    ml_loaded: bool
    packets_processed: int
    flows_analyzed: int
    anomalies_detected: int
    attacks_detected: int


class IDSControlRequest(BaseModel):
    """IDS control command"""
    enabled: bool
    mode: str = "monitor"  # monitor or protect


@router.get("/status", response_model=IDSStatusResponse)
async def get_ids_status(
    current_user: User = Depends(get_current_user)
):
    """Get current IDS status"""
    ids = get_ids_service()
    status_info = ids.get_status()
    
    return IDSStatusResponse(
        enabled=status_info["enabled"],
        mode=status_info["mode"],
        ml_loaded=status_info["ml_loaded"],
        packets_processed=status_info["packets_processed"],
        flows_analyzed=status_info["flows_analyzed"],
        anomalies_detected=status_info["anomalies_detected"],
        attacks_detected=status_info["attacks_detected"],
    )


@router.post("/control", response_model=IDSStatusResponse)
async def control_ids(
    request: IDSControlRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST))
):
    """
    Control IDS - Start or Stop
    
    Requires ADMIN or ANALYST role
    """
    ids = get_ids_service()
    
    # Set mode
    if request.mode in ["monitor", "protect"]:
        await ids.set_mode(request.mode)
    
    # Start or stop IDS
    if request.enabled:
        if not ids.is_enabled():
            success = await ids.start()
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to start IDS - check ML models are loaded"
                )
            logger.info(f"IDS started by {current_user.email}")
    else:
        if ids.is_enabled():
            success = await ids.stop()
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to stop IDS"
                )
            logger.info(f"IDS stopped by {current_user.email}")
    
    # Return updated status
    status_info = ids.get_status()
    return IDSStatusResponse(
        enabled=status_info["enabled"],
        mode=status_info["mode"],
        ml_loaded=status_info["ml_loaded"],
        packets_processed=status_info["packets_processed"],
        flows_analyzed=status_info["flows_analyzed"],
        anomalies_detected=status_info["anomalies_detected"],
        attacks_detected=status_info["attacks_detected"],
    )
