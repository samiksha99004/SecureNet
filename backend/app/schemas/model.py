"""
SecureNet Backend — ML Model Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── Model Status ──────────────────────────────────────────────────────────────

class ModelStatus(str):
    """Model loading status"""
    LOADED = "loaded"
    LOADING = "loading"
    ERROR = "error"
    NOT_LOADED = "not_loaded"


# ── Isolation Forest ──────────────────────────────────────────────────────────

class IsolationForestMetrics(BaseModel):
    """Metrics for Isolation Forest model"""
    rocAuc: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1Score: Optional[float] = None


class IsolationForestInfo(BaseModel):
    """Isolation Forest model information"""
    status: str  # ModelStatus enum value
    version: Optional[str] = None
    nEstimators: Optional[int] = None
    maxSamples: Optional[int] = None
    contamination: Optional[float] = None
    threshold: Optional[float] = None
    featureCount: Optional[int] = None
    featureNames: List[str] = []
    trainedAt: Optional[datetime] = None
    metrics: Optional[IsolationForestMetrics] = None


# ── XGBoost ───────────────────────────────────────────────────────────────────

class PerClassMetric(BaseModel):
    """Per-class classification metrics"""
    className: str
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1Score: Optional[float] = None
    support: Optional[int] = None


class XGBoostMetrics(BaseModel):
    """XGBoost classifier metrics"""
    accuracy: Optional[float] = None
    macroF1: Optional[float] = None
    weightedF1: Optional[float] = None
    perClassMetrics: List[PerClassMetric] = []


class XGBoostInfo(BaseModel):
    """XGBoost model information"""
    status: str  # ModelStatus enum value
    version: Optional[str] = None
    nEstimators: Optional[int] = None
    maxDepth: Optional[int] = None
    learningRate: Optional[float] = None
    featureCount: Optional[int] = None
    featureNames: List[str] = []
    supportedAttackClasses: List[str] = []
    trainedAt: Optional[datetime] = None
    metrics: Optional[XGBoostMetrics] = None


# ── Combined Model Info ───────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    """Combined model information for both stages"""
    isolationForest: Optional[IsolationForestInfo] = None
    xgboost: Optional[XGBoostInfo] = None
    lastRefreshedAt: Optional[datetime] = None


# ── Feature Importance ────────────────────────────────────────────────────────

class FeatureImportance(BaseModel):
    """Feature importance ranking"""
    featureName: str
    importanceScore: float
    rank: int
