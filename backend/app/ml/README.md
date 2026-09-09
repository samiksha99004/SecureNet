# SecureNet ML Pipeline

## Overview

This directory contains the ML inference pipeline for the two-stage intrusion detection system.

## Architecture

### Stage 1: Isolation Forest (Anomaly Detection)
- **Purpose**: Detect anomalous network flows
- **Input**: 78-feature vector per flow
- **Output**: Anomaly score (0-1)
- **Model File**: `models/isolation_forest.joblib`

### Stage 2: XGBoost (Attack Classification)
- **Purpose**: Classify anomalies into attack types
- **Input**: 78-feature vector (same as Stage 1)
- **Output**: Attack class + confidence
- **Model File**: `models/xgboost_classifier.joblib`

## 78-Feature Specification

The system expects exactly 78 features for each network flow. These should include:

### Basic Flow Features
- Flow duration (ms)
- Total forward packets
- Total backward packets
- Total forward bytes
- Total backward bytes
- Forward packet rate
- Backward packet rate
- Flow bytes per second
- Flow packets per second

### Packet Size Features
- Min/max/mean/std forward packet length
- Min/max/mean/std backward packet length

### Inter-arrival Time Features
- Min/max/mean/std forward inter-arrival time
- Min/max/mean/std backward inter-arrival time

### Flag Counts
- FIN, SYN, RST, PSH, ACK, URG, ECE, CWR flag counts

### Additional Features
- Down/Up ratio
- Average packet size
- Subflow forward/backward packets and bytes
- Init window size (forward/backward)
- Active/Idle times (min/max/mean/std)

## Implementation Tasks

### 1. Feature Preprocessing (`preprocessing.py`)
```python
class FeaturePreprocessor:
    def __init__(self, scaler_path: str):
        # Load scaler from file
        pass
    
    def preprocess(self, raw_features: dict) -> np.ndarray:
        # Convert dict to 78-feature array
        # Apply scaling
        # Return preprocessed features
        pass
```

### 2. Isolation Forest (`isolation_forest.py`)
```python
class IsolationForestDetector:
    def __init__(self, model_path: str):
        # Load trained model
        pass
    
    def predict(self, features: np.ndarray) -> tuple[float, bool]:
        # Return (anomaly_score, is_anomaly)
        pass
    
    def get_model_info(self) -> dict:
        # Return model metadata
        pass
```

### 3. XGBoost Classifier (`xgboost_classifier.py`)
```python
class XGBoostClassifier:
    def __init__(self, model_path: str):
        # Load trained model
        pass
    
    def predict(self, features: np.ndarray) -> tuple[str, float]:
        # Return (attack_type, confidence)
        pass
    
    def get_model_info(self) -> dict:
        # Return model metadata
        pass
```

### 4. Inference Pipeline (`inference.py`)
```python
class InferencePipeline:
    def __init__(self):
        self.preprocessor = FeaturePreprocessor(...)
        self.stage1 = IsolationForestDetector(...)
        self.stage2 = XGBoostClassifier(...)
    
    async def analyze_flow(self, raw_features: dict) -> dict:
        # Preprocess
        features = self.preprocessor.preprocess(raw_features)
        
        # Stage 1: Anomaly detection
        anomaly_score, is_anomaly = self.stage1.predict(features)
        
        # Stage 2: Classification (if anomalous)
        if is_anomaly:
            attack_type, confidence = self.stage2.predict(features)
        else:
            attack_type, confidence = None, None
        
        return {
            'anomaly_score': anomaly_score,
            'is_anomaly': is_anomaly,
            'attack_type': attack_type,
            'confidence': confidence
        }
```

## Model Training

Models should be trained separately using your dataset. Training notebooks/scripts should:

1. Extract 78 features from network flows
2. Train Isolation Forest on mixed traffic
3. Train XGBoost on labeled attack data
4. Save models using joblib

## Integration Points

### Creating Security Events

When the ML pipeline detects an anomaly:

```python
from app.models.security_event import SecurityEvent, SeverityLevel, DetectionMode, ActionTaken

event = SecurityEvent(
    source_ip=flow['src_ip'],
    source_port=flow['src_port'],
    destination_ip=flow['dst_ip'],
    destination_port=flow['dst_port'],
    protocol=flow['protocol'],
    anomaly_score=result['anomaly_score'],
    severity=calculate_severity(result['anomaly_score']),
    attack_type=result['attack_type'],
    confidence=result['confidence'],
    mode=DetectionMode.MONITOR,  # or PROTECT based on settings
    action_taken=ActionTaken.LOGGED,
    contributing_features=extract_top_features(features)
)

db.add(event)
await db.commit()
```

### WebSocket Broadcasting

Send live updates:

```python
from app.websocket.manager import manager

await manager.send_live_score({
    'anomalyScore': result['anomaly_score'],
    'severity': severity,
    'sourceIp': flow['src_ip'],
    'destinationIp': flow['dst_ip'],
    'protocol': flow['protocol'],
    'attackType': result['attack_type']
})
```

## Testing

Create test fixtures with synthetic feature vectors:

```python
def test_isolation_forest():
    features = np.random.rand(1, 78)
    detector = IsolationForestDetector('models/isolation_forest.joblib')
    score, is_anomaly = detector.predict(features)
    assert 0 <= score <= 1
```

## Performance Considerations

- **Model Loading**: Load models once at startup, not per request
- **Batch Processing**: Process multiple flows in batches when possible
- **Caching**: Cache preprocessing pipelines
- **Async**: Use async/await for I/O operations
- **Monitoring**: Log inference latency and model performance

## References

- Isolation Forest: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- XGBoost: https://xgboost.readthedocs.io/
- Network Flow Features: CIC-IDS2017 feature documentation
