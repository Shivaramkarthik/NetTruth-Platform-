from typing import List, Dict, Tuple, Optional
from datetime import datetime
import os
from loguru import logger
from app.config import settings

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Mock classes to avoid NameError
    class IsolationForest: pass
    class StandardScaler: pass
    class np:
        @staticmethod
        def array(x): return x
        @staticmethod
        def var(x): return 0
        @staticmethod
        def zeros_like(x): return x
        ndarray = list


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector for network throttling.
    
    Detects unusual patterns in network performance that may indicate
    ISP throttling behavior.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize the anomaly detector."""
        self.model_path = model_path or os.path.join(settings.ML_MODEL_PATH, "anomaly_detector.joblib")
        self.scaler_path = os.path.join(settings.ML_MODEL_PATH, "anomaly_scaler.joblib")
        
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        
        # Feature names for interpretability
        self.feature_names = [
            "download_speed",
            "upload_speed",
            "latency",
            "jitter",
            "packet_loss",
            "download_ratio",  # actual/promised
            "upload_ratio",
            "hour_of_day",
            "day_of_week",
            "speed_variance",  # Rolling variance
            "latency_variance"
        ]
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create a new one."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("Loaded existing anomaly detection model")
            else:
                self._create_new_model()
        except Exception as e:
            logger.warning(f"Error loading model: {e}. Creating new model.")
            self._create_new_model()
    
    def _create_new_model(self):
        """Create a new Isolation Forest model."""
        self.model = IsolationForest(
            n_estimators=200,
            contamination=0.1,  # Expected proportion of anomalies
            max_samples='auto',
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        logger.info("Created new anomaly detection model")
    
    def prepare_features(self, data: List[Dict]) -> np.ndarray:
        """
        Prepare feature matrix from raw network data.
        
        Args:
            data: List of network log dictionaries
            
        Returns:
            Feature matrix as numpy array
        """
        features = []
        
        for i, record in enumerate(data):
            timestamp = record.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # Calculate rolling statistics if we have enough data
            speed_variance = 0
            latency_variance = 0
            if i >= 5:
                recent_speeds = [d.get('download_speed', 0) for d in data[max(0, i-5):i]]
                recent_latencies = [d.get('latency', 0) for d in data[max(0, i-5):i]]
                speed_variance = np.var(recent_speeds) if recent_speeds else 0
                latency_variance = np.var(recent_latencies) if recent_latencies else 0
            
            feature_vector = [
                record.get('download_speed', 0),
                record.get('upload_speed', 0),
                record.get('latency', 0),
                record.get('jitter', 0),
                record.get('packet_loss', 0),
                record.get('download_ratio', 1.0),
                record.get('upload_ratio', 1.0),
                timestamp.hour,
                timestamp.weekday(),
                speed_variance,
                latency_variance
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def train(self, data: List[Dict]) -> Dict:
        """
        Train the anomaly detection model.
        
        Args:
            data: List of network log dictionaries (normal behavior)
            
        Returns:
            Training metrics
        """
        logger.info(f"Training anomaly detector with {len(data)} samples")
        
        X = self.prepare_features(data)
        
        # Fit scaler and transform
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled)
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        
        logger.info("Anomaly detection model trained and saved")
        
        return {
            "samples_trained": len(data),
            "features_used": len(self.feature_names),
            "model_type": "IsolationForest"
        }
    
    def detect(self, data: List[Dict]) -> List[Dict]:
        """
        Detect anomalies in network data.
        
        Args:
            data: List of network log dictionaries
            
        Returns:
            List of detection results with anomaly scores
        """
        if not data:
            return []
        
        X = self.prepare_features(data)
        
        # Check if fitted, if not, return safe defaults
        try:
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Get predictions (-1 for anomaly, 1 for normal)
            predictions = self.model.predict(X_scaled)
            
            # Get anomaly scores (lower = more anomalous)
            scores = self.model.decision_function(X_scaled)
        except (Exception, ValueError) as e:
            logger.warning(f"Model not fitted or scaling error: {e}. Returning safe defaults.")
            return [
                {
                    "index": i,
                    "is_anomaly": False,
                    "anomaly_score": 0.0,
                    "confidence": 0.5,
                    "timestamp": data[i].get('timestamp'),
                    "download_speed": data[i].get('download_speed'),
                    "upload_speed": data[i].get('upload_speed'),
                    "latency": data[i].get('latency')
                }
                for i in range(len(data))
            ]
        
        # Convert scores to confidence (0-1, higher = more confident it's anomaly)
        # Normalize scores to 0-1 range
        min_score, max_score = scores.min(), scores.max()
        if max_score != min_score:
            normalized_scores = 1 - (scores - min_score) / (max_score - min_score)
        else:
            normalized_scores = np.zeros_like(scores)
        
        results = []
        for i, (pred, score, norm_score) in enumerate(zip(predictions, scores, normalized_scores)):
            is_anomaly = pred == -1
            results.append({
                "index": i,
                "is_anomaly": is_anomaly,
                "anomaly_score": float(score),
                "confidence": float(norm_score) if is_anomaly else float(1 - norm_score),
                "timestamp": data[i].get('timestamp'),
                "download_speed": data[i].get('download_speed'),
                "upload_speed": data[i].get('upload_speed'),
                "latency": data[i].get('latency')
            })
        
        return results
    
    def detect_single(self, record: Dict) -> Dict:
        """
        Detect if a single record is anomalous.
        
        Args:
            record: Single network log dictionary
            
        Returns:
            Detection result
        """
        results = self.detect([record])
        return results[0] if results else {}
    
    def get_feature_importance(self, data: List[Dict]) -> Dict[str, float]:
        """
        Estimate feature importance for anomaly detection.
        
        Uses permutation importance approach.
        """
        X = self.prepare_features(data)
        X_scaled = self.scaler.transform(X)
        
        base_scores = self.model.decision_function(X_scaled)
        base_anomaly_rate = np.mean(self.model.predict(X_scaled) == -1)
        
        importance = {}
        for i, feature_name in enumerate(self.feature_names):
            X_permuted = X_scaled.copy()
            np.random.shuffle(X_permuted[:, i])
            
            permuted_scores = self.model.decision_function(X_permuted)
            permuted_anomaly_rate = np.mean(self.model.predict(X_permuted) == -1)
            
            # Importance = change in anomaly detection rate
            importance[feature_name] = abs(permuted_anomaly_rate - base_anomaly_rate)
        
        # Normalize
        total = sum(importance.values())
        if total > 0:
            importance = {k: v/total for k, v in importance.items()}
        
        return importance
