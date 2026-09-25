"""
SecureNet — Two-stage detector (paper, Algorithm 1)

    scaled   ← Scaler.transform(features)
    score    ← IsolationForest.score(scaled)
    if score > θ:
        category    ← XGBoost.predict(scaled)
        topFeatures ← ExplainTop(scaled, category)

Both stages are OPTIONAL. Depending on which artifacts exist in ML_MODELS_DIR
the detector runs as:
  * Isolation Forest + XGBoost  (anomaly gate, then attack classification)
  * Isolation Forest only       (anomalies reported with no attack category)
  * XGBoost only                (every flow classified; non-benign → alert)
  * nothing loaded              (IDS captures traffic but does not score it)

Nothing is loaded at import time; call `load()` (done at startup only when
ML_AUTOLOAD=true, or via POST /api/model/reload).

Isolation Forest anomaly score = -score_samples(x), i.e. the original
Liu et al. score in (0, 1]: ~0.5 is ordinary, → 1 is increasingly anomalous.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.ml.features import FEATURE_COLUMNS
from app.utils.logger import logger

# Artifact file names looked up inside ML_MODELS_DIR (first match wins).
IF_FILES = ("isolation_forest_model.pkl", "isolation_forest.pkl", "isolation_forest.joblib")
XGB_FILES = ("xgboost_multiclass_model.pkl", "xgboost_model.pkl", "xgboost.pkl", "xgboost_classifier.joblib")
SCALER_FILES = ("scaler.pkl", "feature_scaler.joblib")
ENCODER_FILES = ("label_encoder.pkl",)
COLUMNS_FILES = ("feature_columns.pkl",)

BENIGN_LABELS = {"benign", "normal", "0"}


@dataclass
class Detection:
    """Result of scoring one flow."""
    anomaly_score: float                 # 0..1, higher = more anomalous
    is_alert: bool                       # store + alert?
    attack_type: Optional[str] = None    # stage-2 category (None = unknown/none)
    confidence: Optional[float] = None   # stage-2 probability of attack_type
    reason: str = ""
    top_features: List[Dict] = field(default_factory=list)


def _first_existing(directory: Path, names) -> Optional[Path]:
    for name in names:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


class Detector:
    """Holds the optional Isolation Forest / XGBoost models and scores flows."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.isolation_forest = None
        self.xgboost = None
        self.scaler = None
        self.label_encoder = None
        self.feature_columns: List[str] = list(FEATURE_COLUMNS)
        self.xgb_appends_if_score = False
        self.models_dir: Optional[Path] = None
        self.errors: Dict[str, str] = {}

    # ── loading ──────────────────────────────────────────────────────────────

    @property
    def has_isolation_forest(self) -> bool:
        return self.isolation_forest is not None

    @property
    def has_xgboost(self) -> bool:
        return self.xgboost is not None

    @property
    def loaded(self) -> bool:
        return self.has_isolation_forest or self.has_xgboost

    @property
    def name(self) -> str:
        parts = []
        if self.has_isolation_forest:
            parts.append("isolation_forest")
        if self.has_xgboost:
            parts.append("xgboost")
        return "+".join(parts) if parts else "none"

    def load(self, models_dir: Path) -> bool:
        """Load whatever artifacts exist in `models_dir`. Returns self.loaded."""
        self.reset()
        self.models_dir = models_dir
        if not models_dir.is_dir():
            self.errors["models_dir"] = f"Directory not found: {models_dir}"
            logger.warning(self.errors["models_dir"])
            return False

        try:
            import joblib
        except ImportError:
            self.errors["dependencies"] = "ML libraries missing — pip install -r requirements-ml.txt"
            logger.warning(self.errors["dependencies"])
            return False

        def _load(kind: str, names) -> object:
            path = _first_existing(models_dir, names)
            if path is None:
                return None
            try:
                obj = joblib.load(path)
                logger.info(f"Loaded {kind}: {path.name}")
                return obj
            except Exception as exc:
                self.errors[kind] = f"{path.name}: {exc}"
                logger.error(f"Failed to load {kind} from {path}: {exc}")
                return None

        columns = _load("feature_columns", COLUMNS_FILES)
        if columns is not None:
            self.feature_columns = [str(c) for c in list(columns)]
        self.scaler = _load("scaler", SCALER_FILES)
        self.isolation_forest = _load("isolation_forest", IF_FILES)
        self.xgboost = _load("xgboost", XGB_FILES)
        self.label_encoder = _load("label_encoder", ENCODER_FILES)

        n_features = len(self.feature_columns)
        if self.scaler is not None and getattr(self.scaler, "n_features_in_", n_features) != n_features:
            self.errors["scaler"] = "Scaler feature count does not match feature_columns — scaler ignored"
            logger.warning(self.errors["scaler"])
            self.scaler = None
        if self.xgboost is not None:
            expected = getattr(self.xgboost, "n_features_in_", n_features)
            self.xgb_appends_if_score = expected == n_features + 1
            if expected not in (n_features, n_features + 1):
                self.errors["xgboost"] = f"XGBoost expects {expected} features, have {n_features} — disabled"
                logger.error(self.errors["xgboost"])
                self.xgboost = None
            elif self.xgb_appends_if_score and self.isolation_forest is None:
                self.errors["xgboost"] = "This XGBoost model needs the Isolation Forest score as input — disabled"
                logger.error(self.errors["xgboost"])
                self.xgboost = None

        logger.info(f"Detector ready: {self.name}")
        return self.loaded

    # ── metadata ─────────────────────────────────────────────────────────────

    def attack_classes(self) -> List[str]:
        classes = self._classes()
        return [c for c in classes if c.lower() not in BENIGN_LABELS]

    def _classes(self) -> List[str]:
        if self.label_encoder is not None:
            return [str(c) for c in self.label_encoder.classes_]
        if self.xgboost is not None and hasattr(self.xgboost, "classes_"):
            return [str(c) for c in self.xgboost.classes_]
        return []

    def feature_importance(self, limit: int = 20) -> List[Dict]:
        """Global XGBoost feature importances (Isolation Forest has none)."""
        if self.xgboost is None or not hasattr(self.xgboost, "feature_importances_"):
            return []
        names = list(self.feature_columns) + (["IF anomaly score"] if self.xgb_appends_if_score else [])
        pairs = sorted(zip(names, map(float, self.xgboost.feature_importances_)), key=lambda p: p[1], reverse=True)
        return [
            {"feature_name": n, "importance_score": round(s, 6), "rank": i + 1}
            for i, (n, s) in enumerate(pairs[:limit])
        ]

    # ── scoring (CPU-bound: call via asyncio.to_thread) ──────────────────────

    def analyze(
        self,
        features: Dict[str, float],
        threshold: float,
        stage2_enabled: bool = True,
        stage2_confidence: float = 0.0,
    ) -> Optional[Detection]:
        """Score one flow. Returns None when no model is loaded."""
        if not self.loaded:
            return None
        import numpy as np

        raw = np.array(
            [[float(features.get(name, 0.0)) for name in self.feature_columns]], dtype=np.float64
        )
        raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
        scaled = self.scaler.transform(raw) if self.scaler is not None else raw

        # Stage 1 — Isolation Forest
        if_score = None
        if self.isolation_forest is not None:
            if_score = float(-self.isolation_forest.score_samples(scaled)[0])
            if if_score <= threshold:
                return Detection(anomaly_score=if_score, is_alert=False)

        # Stage 2 — XGBoost
        label, confidence, benign_p = None, None, None
        if self.xgboost is not None and (stage2_enabled or self.isolation_forest is None):
            x2 = scaled
            if self.xgb_appends_if_score:
                decision = float(self.isolation_forest.decision_function(scaled)[0])
                x2 = np.column_stack([scaled, [decision]])
            proba = self.xgboost.predict_proba(x2)[0]
            idx = int(np.argmax(proba))
            classes = self._classes()
            label = classes[idx] if idx < len(classes) else str(idx)
            confidence = float(proba[idx])
            benign_idx = next((i for i, c in enumerate(classes) if c.lower() in BENIGN_LABELS), None)
            benign_p = float(proba[benign_idx]) if benign_idx is not None else None

        top = self._top_features(scaled[0])

        if if_score is not None:
            attack_type = None
            if label is not None and label.lower() not in BENIGN_LABELS and confidence >= stage2_confidence:
                attack_type = label
            reason = f"Isolation Forest anomaly score {if_score:.3f} exceeded threshold {threshold:.2f}"
            if label is not None:
                reason += f"; XGBoost: {label} ({confidence:.0%})"
            return Detection(if_score, True, attack_type, confidence if attack_type else None, reason, top)

        # XGBoost only
        anomaly = 1.0 - benign_p if benign_p is not None else confidence or 0.0
        is_attack = label is not None and label.lower() not in BENIGN_LABELS and confidence >= stage2_confidence
        return Detection(
            anomaly_score=anomaly,
            is_alert=is_attack,
            attack_type=label if is_attack else None,
            confidence=confidence if is_attack else None,
            reason=f"XGBoost classified flow as {label} ({confidence:.0%})",
            top_features=top if is_attack else [],
        )

    def _top_features(self, row, k: int = 5) -> List[Dict]:
        """ExplainTop: features furthest from the training distribution.

        With a StandardScaler the scaled value is a z-score, so |z| is a
        direct measure of how unusual the feature is. XGBoost importances
        (when available) weight the ranking toward features the model uses.
        """
        weights = None
        if self.xgboost is not None and hasattr(self.xgboost, "feature_importances_"):
            weights = list(self.xgboost.feature_importances_)[: len(self.feature_columns)]
        scored = []
        for i, name in enumerate(self.feature_columns):
            value = float(row[i])
            if not math.isfinite(value):
                continue
            contribution = abs(value) * (float(weights[i]) if weights else 1.0)
            scored.append((name, value, contribution))
        scored.sort(key=lambda t: t[2], reverse=True)
        return [
            {"name": n, "value": round(v, 4), "contribution": round(c, 4)}
            for n, v, c in scored[:k] if c > 0
        ]


detector = Detector()


def get_detector() -> Detector:
    return detector
