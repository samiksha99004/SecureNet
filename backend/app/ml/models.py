"""
SecureNet ML Models - Real Integration

Loads and uses the actual trained models from F:\all_10_csv_manual:
- isolation_forest_model.pkl (71 features)
- xgboost_hybrid_model.pkl (72 features: 71 + IF anomaly score)
- xgboost_multiclass_model.pkl (attack type classification)
- scaler.pkl (feature scaling)
- label_encoder.pkl (attack type labels)
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from app.utils.logger import logger

# REAL ML MODEL PATHS - from F:\all_10_csv_manual
ML_DIR = r"F:\all_10_csv_manual"

ISOLATION_FOREST_PATH = os.path.join(ML_DIR, "isolation_forest_model.pkl")
XGBOOST_HYBRID_PATH = os.path.join(ML_DIR, "xgboost_hybrid_model.pkl")
XGBOOST_MULTICLASS_PATH = os.path.join(ML_DIR, "xgboost_multiclass_model.pkl")
XGBOOST_THRESHOLD_PATH = os.path.join(ML_DIR, "xgboost_threshold.pkl")
SCALER_PATH = os.path.join(ML_DIR, "scaler.pkl")
FEATURE_COLUMNS_PATH = os.path.join(ML_DIR, "feature_columns.pkl")
HYBRID_FEATURE_COLUMNS_PATH = os.path.join(ML_DIR, "hybrid_feature_columns.pkl")
LABEL_ENCODER_PATH = os.path.join(ML_DIR, "label_encoder.pkl")


class MLModels:
    """Manages the real trained ML models"""
    
    def __init__(self):
        self.isolation_forest = None
        self.xgboost_hybrid = None
        self.xgboost_multiclass = None
        self.xgboost_threshold = 0.3  # default
        self.scaler = None
        self.feature_columns = None
        self.hybrid_feature_columns = None
        self.label_encoder = None
        self.loaded = False
        
    def load_models(self) -> bool:
        """Load all ML models from disk"""
        try:
            logger.info("Loading ML models from F:\\all_10_csv_manual...")
            
            # Load Isolation Forest
            if os.path.exists(ISOLATION_FOREST_PATH):
                self.isolation_forest = joblib.load(ISOLATION_FOREST_PATH)
                logger.info(f"✓ Isolation Forest loaded")
            else:
                logger.error(f"✗ Isolation Forest not found: {ISOLATION_FOREST_PATH}")
                return False
            
            # Load feature columns (71 features)
            if os.path.exists(FEATURE_COLUMNS_PATH):
                self.feature_columns = joblib.load(FEATURE_COLUMNS_PATH)
                logger.info(f"✓ Feature columns loaded: {len(self.feature_columns)} features")
            else:
                logger.error(f"✗ Feature columns not found: {FEATURE_COLUMNS_PATH}")
                return False
            
            # Load XGBoost hybrid model (binary: normal/attack)
            if os.path.exists(XGBOOST_HYBRID_PATH):
                self.xgboost_hybrid = joblib.load(XGBOOST_HYBRID_PATH)
                logger.info(f"✓ XGBoost hybrid model loaded")
                
                # Load threshold
                if os.path.exists(XGBOOST_THRESHOLD_PATH):
                    self.xgboost_threshold = joblib.load(XGBOOST_THRESHOLD_PATH)
                    logger.info(f"✓ XGBoost threshold loaded: {self.xgboost_threshold}")
            else:
                logger.warning(f"⚠ XGBoost hybrid model not found: {XGBOOST_HYBRID_PATH}")
            
            # Load hybrid feature columns
            if os.path.exists(HYBRID_FEATURE_COLUMNS_PATH):
                self.hybrid_feature_columns = joblib.load(HYBRID_FEATURE_COLUMNS_PATH)
                logger.info(f"✓ Hybrid feature columns loaded: {len(self.hybrid_feature_columns)} features")
            
            # Load XGBoost multiclass model (attack type classification)
            if os.path.exists(XGBOOST_MULTICLASS_PATH):
                self.xgboost_multiclass = joblib.load(XGBOOST_MULTICLASS_PATH)
                logger.info(f"✓ XGBoost multiclass model loaded")
            else:
                logger.warning(f"⚠ XGBoost multiclass model not found: {XGBOOST_MULTICLASS_PATH}")
            
            # Load label encoder (attack type names)
            if os.path.exists(LABEL_ENCODER_PATH):
                self.label_encoder = joblib.load(LABEL_ENCODER_PATH)
                attack_types = list(self.label_encoder.classes_)
                logger.info(f"✓ Label encoder loaded: {len(attack_types)} classes")
                logger.info(f"  Attack types: {attack_types}")
            else:
                logger.warning(f"⚠ Label encoder not found: {LABEL_ENCODER_PATH}")
            
            # Load scaler (if exists)
            if os.path.exists(SCALER_PATH):
                self.scaler = joblib.load(SCALER_PATH)
                logger.info(f"✓ Scaler loaded")
            else:
                logger.warning(f"⚠ Scaler not found (may not be needed): {SCALER_PATH}")
            
            self.loaded = True
            logger.info("✓ ML models loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to load ML models: {e}", exc_info=True)
            self.loaded = False
            return False
    
    def get_feature_count(self) -> int:
        """Get the number of features expected by the model"""
        if self.feature_columns:
            return len(self.feature_columns)
        return 0
    
    def get_feature_names(self) -> List[str]:
        """Get the list of feature names"""
        if self.feature_columns:
            return self.feature_columns.copy()
        return []
    
    def get_attack_types(self) -> List[str]:
        """Get the list of possible attack types"""
        if self.label_encoder:
            # Exclude 'Benign' from attack types
            types = [t for t in self.label_encoder.classes_ if t != 'Benign']
            return types
        return []
    
    def predict_anomaly(self, features: np.ndarray) -> Tuple[float, bool]:
        """
        Stage 1: Isolation Forest anomaly detection
        
        Args:
            features: numpy array of shape (n_samples, 71)
        
        Returns:
            (anomaly_score, is_anomaly)
            - anomaly_score: float (higher = more normal, lower/negative = more anomalous)
            - is_anomaly: bool (True if anomalous)
        """
        if not self.loaded or self.isolation_forest is None:
            raise RuntimeError("ML models not loaded")
        
        try:
            # Get anomaly score from Isolation Forest
            # decision_function returns higher values for normal samples
            anomaly_scores = self.isolation_forest.decision_function(features)
            
            # predict returns 1 for inliers (normal), -1 for outliers (anomalous)
            predictions = self.isolation_forest.predict(features)
            
            # Convert to boolean: -1 (outlier) -> True (anomaly), 1 (inlier) -> False (normal)
            is_anomalies = predictions == -1
            
            return anomaly_scores, is_anomalies
            
        except Exception as e:
            logger.error(f"Anomaly prediction failed: {e}")
            raise
    
    def predict_binary(self, features: np.ndarray, if_scores: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Stage 2a: Binary classification (normal/attack) using hybrid model
        
        Args:
            features: numpy array of shape (n_samples, 71)
            if_scores: anomaly scores from Isolation Forest
        
        Returns:
            (predictions, probabilities)
            - predictions: array of 0 (normal) or 1 (attack)
            - probabilities: array of attack probabilities
        """
        if not self.loaded or self.xgboost_hybrid is None:
            raise RuntimeError("XGBoost hybrid model not loaded")
        
        try:
            # Combine features with IF anomaly score
            if self.hybrid_feature_columns and len(self.hybrid_feature_columns) == len(self.feature_columns) + 1:
                # Add IF score as extra feature
                features_with_if = np.column_stack([features, if_scores])
            else:
                features_with_if = features
            
            # Get probabilities
            probabilities = self.xgboost_hybrid.predict_proba(features_with_if)[:, 1]
            
            # Apply threshold
            predictions = (probabilities >= self.xgboost_threshold).astype(int)
            
            return predictions, probabilities
            
        except Exception as e:
            logger.error(f"Binary prediction failed: {e}")
            raise
    
    def predict_multiclass(self, features: np.ndarray, if_scores: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Stage 2b: Multi-class classification (attack type)
        
        Args:
            features: numpy array of shape (n_samples, 71)
            if_scores: anomaly scores from Isolation Forest
        
        Returns:
            (predicted_classes, predicted_labels, confidences)
            - predicted_classes: array of class indices
            - predicted_labels: array of attack type names
            - confidences: array of confidence scores
        """
        if not self.loaded or self.xgboost_multiclass is None or self.label_encoder is None:
            raise RuntimeError("XGBoost multiclass model or label encoder not loaded")
        
        try:
            # Add IF score as extra feature if model expects it
            if self.hybrid_feature_columns and len(self.hybrid_feature_columns) == len(self.feature_columns) + 1:
                features_with_if = np.column_stack([features, if_scores])
            else:
                features_with_if = features
            
            # Get predictions
            predicted_classes = self.xgboost_multiclass.predict(features_with_if)
            
            # Get probabilities for confidence
            probabilities = self.xgboost_multiclass.predict_proba(features_with_if)
            confidences = np.max(probabilities, axis=1)
            
            # Convert class indices to labels
            predicted_labels = self.label_encoder.inverse_transform(predicted_classes)
            
            return predicted_classes, predicted_labels, confidences
            
        except Exception as e:
            logger.error(f"Multiclass prediction failed: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """Get information about loaded models"""
        info = {
            "loaded": self.loaded,
            "isolation_forest": {
                "status": "loaded" if self.isolation_forest else "not_loaded",
                "n_estimators": getattr(self.isolation_forest, 'n_estimators', None) if self.isolation_forest else None,
                "contamination": getattr(self.isolation_forest, 'contamination', None) if self.isolation_forest else None,
            },
            "xgboost_hybrid": {
                "status": "loaded" if self.xgboost_hybrid else "not_loaded",
                "threshold": self.xgboost_threshold if self.xgboost_hybrid else None,
            },
            "xgboost_multiclass": {
                "status": "loaded" if self.xgboost_multiclass else "not_loaded",
                "n_classes": len(self.label_encoder.classes_) if self.label_encoder else None,
            },
            "features": {
                "count": len(self.feature_columns) if self.feature_columns else 0,
                "names": self.feature_columns[:10] if self.feature_columns else [],  # First 10
            },
            "attack_types": self.get_attack_types() if self.label_encoder else [],
        }
        return info


# Global ML models instance
ml_models = MLModels()


def initialize_ml_models() -> bool:
    """Initialize ML models on application startup"""
    return ml_models.load_models()


def get_ml_models() -> MLModels:
    """Get the global ML models instance"""
    return ml_models
