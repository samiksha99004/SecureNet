"""
ML Models - Ensemble Architecture (ML-NIDS-main)
Random Forest + XGBoost Ensemble with Autoencoder feature extraction
"""

import json
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import joblib
import torch
import torch.nn as nn
from app.utils.logger import logger

# Model directory
ML_DIR = Path(r"F:\ML-NIDS-main\ML-NIDS-main\models")


class Autoencoder(nn.Module):
    """Autoencoder for feature extraction (77 -> 64 -> 32 -> 16)"""
    
    def __init__(self, input_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.LeakyReLU(0.01),
            nn.Linear(64, 32),
            nn.LeakyReLU(0.01),
            nn.Linear(32, 16),
        )
        self.decoder = nn.Sequential(
            nn.Linear(16, 32),
            nn.LeakyReLU(0.01),
            nn.Linear(32, 64),
            nn.LeakyReLU(0.01),
            nn.Linear(64, input_dim),
            nn.Sigmoid(),
        )
    
    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(values))
    
    def encode(self, values: torch.Tensor) -> torch.Tensor:
        return self.encoder(values)


class EnsembleMLModels:
    """Ensemble ML detection system"""
    
    def __init__(self):
        self.loaded = False
        
        # Feature pipeline
        self.feature_columns = []
        self.imputer = None
        self.scaler = None
        self.selected_indices = None
        
        # Autoencoder
        self.autoencoder = None
        self.latent_scaler = None
        
        # Classifiers
        self.random_forest = None
        self.xgboost = None
        self.label_encoder = None
        
        # Ensemble config
        self.ensemble_weight = 0.5  # RF weight (1-weight = XGBoost weight)
        self.thresholds = None
        
        # Classes
        self.classes = []
        self.benign_index = 0
    
    def load_models(self) -> bool:
        """Load all model artifacts"""
        try:
            logger.info(f"Loading ML models from {ML_DIR}...")
            
            # 1. Feature columns
            with open(ML_DIR / "feature_cols.json", 'r') as f:
                self.feature_columns = json.load(f)
            logger.info(f"✓ Feature columns loaded: {len(self.feature_columns)} features")
            
            # 2. Imputer (for missing values)
            self.imputer = joblib.load(ML_DIR / "imputer.pkl")
            logger.info("✓ Imputer loaded")
            
            # 3. Scaler (for input features)
            self.scaler = joblib.load(ML_DIR / "scaler.pkl")
            logger.info("✓ Scaler loaded")
            
            # 4. Selected feature indices
            self.selected_indices = np.load(ML_DIR / "selected_indices.npy")
            logger.info(f"✓ Selected indices loaded: {len(self.selected_indices)} features")
            
            # 5. Autoencoder
            self.autoencoder = Autoencoder(len(self.feature_columns))
            state_dict = torch.load(ML_DIR / "autoencoder.pth", map_location="cpu", weights_only=True)
            self.autoencoder.load_state_dict(state_dict)
            self.autoencoder.eval()
            logger.info("✓ Autoencoder loaded")
            
            # 6. Latent scaler (for autoencoder output)
            self.latent_scaler = joblib.load(ML_DIR / "latent_scaler.pkl")
            logger.info("✓ Latent scaler loaded")
            
            # 7. Random Forest
            self.random_forest = joblib.load(ML_DIR / "random_forest.pkl")
            self.random_forest.verbose = 0
            logger.info("✓ Random Forest loaded")
            
            # 8. XGBoost
            self.xgboost = joblib.load(ML_DIR / "xgboost.pkl")
            logger.info("✓ XGBoost loaded")
            
            # 9. Label encoder
            self.label_encoder = joblib.load(ML_DIR / "label_encoder.pkl")
            self.classes = [str(cls) for cls in self.label_encoder.classes_]
            self.benign_index = self.classes.index("Benign")
            logger.info(f"✓ Label encoder loaded: {len(self.classes)} classes")
            logger.info(f"  Attack types: {', '.join([c for c in self.classes if c != 'Benign'])}")
            
            # 10. Ensemble weight
            weights = np.load(ML_DIR / "ensemble_weight.npy")
            self.ensemble_weight = float(weights[0])
            logger.info(f"✓ Ensemble weights: RF={self.ensemble_weight:.2f}, XGBoost={1-self.ensemble_weight:.2f}")
            
            # 11. Thresholds
            self.thresholds = np.load(ML_DIR / "thresholds_ensemble.npy")
            logger.info(f"✓ Thresholds loaded: {len(self.thresholds)} per-class thresholds")
            
            self.loaded = True
            logger.info("✅ All ML models loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}", exc_info=True)
            return False
    
    def prepare_features(self, features: np.ndarray) -> np.ndarray:
        """
        Prepare features through the pipeline:
        1. Impute missing values
        2. Scale features
        3. Select features
        4. Extract latent features from autoencoder
        5. Concatenate selected + latent features
        """
        # Ensure 2D array
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Replace inf with nan
        features = np.where(np.isinf(features), np.nan, features)
        
        # 1. Impute missing values
        imputed = self.imputer.transform(features.astype(np.float64))
        
        # 2. Scale features
        scaled = self.scaler.transform(imputed).astype(np.float32)
        
        # 3. Select features
        selected = scaled[:, self.selected_indices]
        
        # 4. Extract latent features from autoencoder
        with torch.no_grad():
            latent = self.autoencoder.encode(torch.from_numpy(scaled)).cpu().numpy()
        
        # 5. Scale latent features
        latent_scaled = self.latent_scaler.transform(latent)
        
        # 6. Concatenate selected + latent
        hybrid = np.concatenate([selected, latent_scaled], axis=1).astype(np.float32)
        
        return hybrid
    
    def predict(self, features: np.ndarray) -> Tuple[str, float, float]:
        """
        Predict attack type using ensemble
        Returns: (label, confidence, threat_score)
        """
        if not self.loaded:
            raise RuntimeError("Models not loaded")
        
        # Prepare features
        hybrid = self.prepare_features(features)
        
        # Get predictions from both models
        rf_probs = self.random_forest.predict_proba(hybrid)
        xgb_probs = self.xgboost.predict_proba(hybrid)
        
        # Ensemble probabilities
        ensemble_probs = (
            self.ensemble_weight * rf_probs +
            (1.0 - self.ensemble_weight) * xgb_probs
        )
        
        # Apply calibrated thresholds
        predictions = self._calibrated_predictions(ensemble_probs)
        
        # Get result for first sample
        predicted_idx = predictions[0]
        label = self.classes[predicted_idx]
        confidence = float(ensemble_probs[0, predicted_idx])
        threat_score = 1.0 - float(ensemble_probs[0, self.benign_index])
        
        return label, confidence, threat_score
    
    def _calibrated_predictions(self, probabilities: np.ndarray) -> np.ndarray:
        """Apply per-class thresholds to predictions"""
        # Mask probabilities below threshold
        masked = np.where(probabilities >= self.thresholds, probabilities, -1.0)
        
        # If no class meets threshold, use max probability
        no_qualifying_class = np.all(masked < 0, axis=1)
        predictions = np.argmax(masked, axis=1)
        predictions[no_qualifying_class] = np.argmax(
            probabilities[no_qualifying_class], axis=1
        )
        
        return predictions
    
    def get_feature_names(self) -> list:
        """Get list of required feature names"""
        return self.feature_columns
    
    def get_attack_types(self) -> list:
        """Get list of detectable attack types"""
        return [cls for cls in self.classes if cls != "Benign"]


def initialize_ml_models() -> bool:
    """Initialize the ensemble ML models"""
    global _ml_models
    _ml_models = EnsembleMLModels()
    return _ml_models.load_models()


def get_ml_models() -> EnsembleMLModels:
    """Get the global ML models instance"""
    return _ml_models


# Global instance
_ml_models = EnsembleMLModels()
