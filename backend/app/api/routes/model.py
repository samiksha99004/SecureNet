"""
SecureNet Backend — ML Model Routes

Status of the optional Isolation Forest / XGBoost models, feature importance,
and an admin endpoint to (re)load models from ML_MODELS_DIR without a restart.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, require_admin
from app.ml.detector import get_detector
from app.ml.ids_service import get_ids_service
from app.models.user import User
from app.schemas.model import FeatureImportance, IsolationForestInfo, ModelInfo, XGBoostInfo
from app.utils.timeutil import utcnow

router = APIRouter(prefix="/model", tags=["ML Model"])


def _status(loaded: bool, error_key: str) -> str:
    detector = get_detector()
    if loaded:
        return "loaded"
    return "error" if error_key in detector.errors else "not_loaded"


def build_model_info() -> ModelInfo:
    detector = get_detector()
    ids = get_ids_service()
    names = detector.feature_columns

    iso = detector.isolation_forest
    if_info = IsolationForestInfo(
        status=_status(iso is not None, "isolation_forest"),
        version=f"scikit-learn {getattr(iso, '_sklearn_version', '')}".strip() if iso is not None else None,
        n_estimators=getattr(iso, "n_estimators", None),
        max_samples=getattr(iso, "max_samples_", None),
        contamination=(iso.contamination if iso is not None and isinstance(iso.contamination, float) else None),
        threshold=ids.config.anomaly_threshold,
        feature_count=len(names),
        feature_names=names if iso is not None else [],
    )

    xgb = detector.xgboost
    params = xgb.get_params() if xgb is not None and hasattr(xgb, "get_params") else {}
    xgb_info = XGBoostInfo(
        status=_status(xgb is not None, "xgboost"),
        version="xgboost" if xgb is not None else None,
        n_estimators=params.get("n_estimators"),
        max_depth=params.get("max_depth"),
        learning_rate=params.get("learning_rate"),
        feature_count=len(names) + (1 if detector.xgb_appends_if_score else 0),
        feature_names=names if xgb is not None else [],
        supported_attack_classes=detector.attack_classes(),
    )
    return ModelInfo(isolation_forest=if_info, xgboost=xgb_info, last_refreshed_at=utcnow())


@router.get("/info", response_model=ModelInfo)
async def get_model_info(current_user: User = Depends(get_current_user)):
    """Information about both detection stages."""
    return build_model_info()


@router.get("/feature-importance", response_model=List[FeatureImportance])
async def get_feature_importance(
    stage: int = Query(2, ge=1, le=2),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Global feature importance. Only XGBoost (stage 2) provides one; stage 1 returns []."""
    if stage == 1:
        return []
    return [FeatureImportance(**item) for item in get_detector().feature_importance(limit)]


@router.post("/reload", response_model=ModelInfo)
async def reload_models(current_user: User = Depends(require_admin)):
    """Load whatever model artifacts are present in ML_MODELS_DIR (admin only)."""
    ids = get_ids_service()
    loaded = await ids.reload_models()
    if not loaded:
        detail = "; ".join(get_detector().errors.values()) or "No model files found in ML_MODELS_DIR"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
    return build_model_info()
