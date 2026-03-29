"""Classification model for throttling type detection."""
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score
import joblib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import os
from loguru import logger

from app.config import settings


class ThrottlingClassifier:
    """
    Multi-class classifier for identifying throttling types.
    
    Classifies detected anomalies into:
    - time_based: Speed drops at specific times
    - app_specific: Throttling specific apps/services
    - data_cap: FUP/data cap throttling
    - peak_hours: Peak hour throttling
    - general: General speed degradation
    - normal: No throttling (false positive from anomaly detector)
    """
    
    THROTTLING_TYPES = [
        "normal",
        "time_based",
        "app_specific",
        "data_cap",
        "peak_hours",
        "general"
    ]
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize the throttling classifier."""
        self.model_path = model_path or os.path.join(settings.ML_MODEL_PATH, "throttling_classifier.joblib")
        self.scaler_path = os.path.join(settings.ML_MODEL_PATH, "classifier_scaler.joblib")
        self.encoder_path = os.path.join(settings.ML_MODEL_PATH, "label_encoder.joblib")
        
        self.model: Optional[GradientBoostingClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.label_encoder: Optional[LabelEncoder] = None
        
        # Extended feature set for classification
        self.feature_names = [
            # Speed metrics
            "download_speed",
            "upload_speed",
            "download_ratio",
            "upload_ratio",
            "speed_drop_percent",
            
            # Latency metrics
            "latency",
            "jitter",
            "packet_loss",
            
            # Time features
            "hour_of_day",
            "day_of_week",
            "is_peak_hour",  # 6-10 PM
            "is_weekend",
            
            # Pattern features
            "speed_variance_1h",
            "speed_variance_24h",
            "latency_spike",
            
            # Service-specific
            "is_streaming_test",
            "is_gaming_test",
            "is_general_test",
            
            # Data usage context
            "data_used_percent",  # Percentage of monthly cap used
            "days_into_cycle",
            
            # Historical patterns
            "similar_time_avg_speed",
            "deviation_from_normal"
        ]
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create a new one."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.label_encoder = joblib.load(self.encoder_path)
                logger.info("Loaded existing throttling classifier")
            else:
                self._create_new_model()
        except Exception as e:
            logger.warning(f"Error loading classifier: {e}. Creating new model.")
            self._create_new_model()
    
    def _create_new_model(self):
        """Create a new classification model."""
        self.model = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.1,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(self.THROTTLING_TYPES)
        logger.info("Created new throttling classifier")
    
    def prepare_features(self, data: List[Dict], historical_data: Optional[List[Dict]] = None) -> np.ndarray:
        """
        Prepare feature matrix for classification.
        
        Args:
            data: List of network log dictionaries
            historical_data: Optional historical data for pattern analysis
            
        Returns:
            Feature matrix as numpy array
        """
        features = []
        
        for i, record in enumerate(data):
            timestamp = record.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            hour = timestamp.hour
            day = timestamp.weekday()
            
            # Calculate derived features
            download_ratio = record.get('download_ratio', 1.0)
            speed_drop = max(0, (1 - download_ratio) * 100)
            
            is_peak = 1 if 18 <= hour <= 22 else 0
            is_weekend = 1 if day >= 5 else 0
            
            # Calculate variances from historical data
            speed_var_1h = record.get('speed_variance_1h', 0)
            speed_var_24h = record.get('speed_variance_24h', 0)
            
            latency_spike = 1 if record.get('latency', 0) > record.get('avg_latency', 50) * 2 else 0
            
            # Service type flags
            target_service = record.get('target_service', 'general').lower()
            is_streaming = 1 if target_service in ['youtube', 'netflix', 'prime', 'hotstar', 'streaming'] else 0
            is_gaming = 1 if target_service in ['gaming', 'steam', 'xbox', 'playstation'] else 0
            is_general = 1 if target_service in ['general', 'speedtest', ''] else 0
            
            # Data usage context
            data_used_percent = record.get('data_used_percent', 50)
            days_into_cycle = record.get('days_into_cycle', 15)
            
            # Historical comparison
            similar_time_avg = record.get('similar_time_avg_speed', record.get('download_speed', 50))
            deviation = (record.get('download_speed', 50) - similar_time_avg) / max(similar_time_avg, 1)
            
            feature_vector = [
                record.get('download_speed', 0),
                record.get('upload_speed', 0),
                download_ratio,
                record.get('upload_ratio', 1.0),
                speed_drop,
                record.get('latency', 0),
                record.get('jitter', 0),
                record.get('packet_loss', 0),
                hour,
                day,
                is_peak,
                is_weekend,
                speed_var_1h,
                speed_var_24h,
                latency_spike,
                is_streaming,
                is_gaming,
                is_general,
                data_used_percent,
                days_into_cycle,
                similar_time_avg,
                deviation
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def train(self, data: List[Dict], labels: List[str]) -> Dict:
        """
        Train the throttling classifier.
        
        Args:
            data: List of network log dictionaries
            labels: List of throttling type labels
            
        Returns:
            Training metrics
        """
        logger.info(f"Training throttling classifier with {len(data)} samples")
        
        X = self.prepare_features(data)
        y = self.label_encoder.transform(labels)
        
        # Fit scaler and transform
        X_scaled = self.scaler.fit_transform(X)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=5)
        
        # Train final model
        self.model.fit(X_scaled, y)
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        joblib.dump(self.label_encoder, self.encoder_path)
        
        logger.info(f"Classifier trained. CV accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")
        
        return {
            "samples_trained": len(data),
            "cv_accuracy": float(cv_scores.mean()),
            "cv_std": float(cv_scores.std()),
            "classes": self.THROTTLING_TYPES
        }
    
    def classify(self, data: List[Dict]) -> List[Dict]:
        """
        Classify throttling type for network data.
        
        Args:
            data: List of network log dictionaries
            
        Returns:
            List of classification results
        """
        if not data:
            return []
        
        X = self.prepare_features(data)
        X_scaled = self.scaler.transform(X)
        
        # Get predictions and probabilities
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        
        results = []
        for i, (pred, probs) in enumerate(zip(predictions, probabilities)):
            throttling_type = self.label_encoder.inverse_transform([pred])[0]
            confidence = float(probs.max())
            
            # Get all class probabilities
            class_probs = {
                self.label_encoder.inverse_transform([j])[0]: float(p)
                for j, p in enumerate(probs)
            }
            
            results.append({
                "index": i,
                "throttling_type": throttling_type,
                "confidence": confidence,
                "is_throttling": throttling_type != "normal",
                "class_probabilities": class_probs,
                "timestamp": data[i].get('timestamp')
            })
        
        return results
    
    def classify_single(self, record: Dict) -> Dict:
        """
        Classify a single record.
        
        Args:
            record: Single network log dictionary
            
        Returns:
            Classification result
        """
        results = self.classify([record])
        return results[0] if results else {}
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance from the trained model.
        """
        if hasattr(self.model, 'feature_importances_'):
            importance = dict(zip(self.feature_names, self.model.feature_importances_))
            return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        return {}
    
    def explain_prediction(self, record: Dict, result: Dict) -> str:
        """
        Generate human-readable explanation for a prediction.
        
        Args:
            record: Input network log
            result: Classification result
            
        Returns:
            Explanation string
        """
        throttling_type = result.get('throttling_type', 'unknown')
        confidence = result.get('confidence', 0)
        
        explanations = {
            "normal": "Network performance appears normal with no signs of throttling.",
            "time_based": f"Speed reduction detected at specific time ({record.get('timestamp', 'unknown')}). This pattern suggests time-based throttling by your ISP.",
            "app_specific": f"Throttling detected for {record.get('target_service', 'specific service')}. Your ISP may be limiting bandwidth for this service.",
            "data_cap": "Speed reduction consistent with FUP (Fair Usage Policy) throttling. You may have exceeded your data cap.",
            "peak_hours": "Speed reduction during peak hours (6-10 PM). This is common ISP behavior during high-demand periods.",
            "general": "General speed degradation detected. Your connection is performing below promised speeds."
        }
        
        base_explanation = explanations.get(throttling_type, "Unknown throttling pattern detected.")
        
        return f"{base_explanation} (Confidence: {confidence*100:.1f}%)"
