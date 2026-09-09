"""
SecureNet Backend — ML Model Routes

Provides information about the ML models (Isolation Forest + XGBoost).
Returns actual model status when models are loaded, otherwise returns not_loaded status.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.model import ModelInfo, IsolationForestInfo, XGBoostInfo
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/model", tags=["ML Model"])


@router.get("/info", response_model=ModelInfo)
async def get_model_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get ML model information for both stages.
    
    Returns actual model metadata from loaded models.
    """
    from app.ml.models import get_ml_models
    
    ml_models = get_ml_models()
    
    if not ml_models.loaded:
        # Models not loaded
        isolation_forest_info = IsolationForestInfo(
            status="not_loaded",
            version=None,
            nEstimators=None,
            maxSamples=None,
            contamination=None,
            threshold=None,
            featureCount=71,
            featureNames=[],
            trainedAt=None,
            metrics=None
        )
        
        xgboost_info = XGBoostInfo(
            status="not_loaded",
            version=None,
            nEstimators=None,
            maxDepth=None,
            learningRate=None,
            featureCount=71,
            featureNames=[],
            supportedAttackClasses=[],
            trainedAt=None,
            metrics=None
        )
        
        return ModelInfo(
            isolationForest=isolation_forest_info,
            xgboost=xgboost_info,
            lastRefreshedAt=datetime.utcnow()
        )
    
    # Get real model information
    model_info_dict = ml_models.get_model_info()
    
    # Isolation Forest info
    if_info = model_info_dict["isolation_forest"]
    isolation_forest_info = IsolationForestInfo(
        status=if_info["status"],
        version="sklearn",
        nEstimators=if_info.get("n_estimators"),
        maxSamples=None,
        contamination=if_info.get("contamination"),
        threshold=None,
        featureCount=model_info_dict["features"]["count"],
        featureNames=model_info_dict["features"]["names"],
        trainedAt=None,
        metrics=None
    )
    
    # XGBoost info
    xgb_info = model_info_dict["xgboost_multiclass"]
    xgboost_info = XGBoostInfo(
        status=xgb_info["status"],
        version="xgboost",
        nEstimators=None,
        maxDepth=None,
        learningRate=None,
        featureCount=model_info_dict["features"]["count"],
        featureNames=model_info_dict["features"]["names"],
        supportedAttackClasses=model_info_dict["attack_types"],
        trainedAt=None,
        metrics=None
    )
    
    return ModelInfo(
        isolationForest=isolation_forest_info,
        xgboost=xgboost_info,
        lastRefreshedAt=datetime.utcnow()
    )
