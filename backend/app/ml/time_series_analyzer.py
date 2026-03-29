"""Time series analysis using LSTM for pattern detection."""
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import os
from loguru import logger

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. LSTM features disabled.")

from app.config import settings


class LSTMModel(nn.Module):
    """LSTM model for time series pattern detection."""
    
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2, output_size: int = 1):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, output_size)
        )
    
    def forward(self, x):
        # LSTM forward pass
        lstm_out, _ = self.lstm(x)
        # Take the last output
        last_output = lstm_out[:, -1, :]
        # Fully connected layers
        output = self.fc(last_output)
        return output


class TimeSeriesAnalyzer:
    """
    LSTM-based time series analyzer for network performance patterns.
    
    Capabilities:
    - Detect recurring throttling patterns
    - Identify time-based speed variations
    - Predict future network performance
    - Detect anomalous sequences
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize the time series analyzer."""
        self.model_path = model_path or os.path.join(settings.ML_MODEL_PATH, "lstm_model.pt")
        
        self.sequence_length = 24  # 24 data points (e.g., hourly for a day)
        self.input_size = 5  # Features per time step
        self.hidden_size = 64
        self.num_layers = 2
        
        self.model: Optional[LSTMModel] = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if TORCH_AVAILABLE else None
        
        self.feature_names = [
            "download_speed",
            "upload_speed",
            "latency",
            "hour_sin",  # Cyclical encoding of hour
            "hour_cos"
        ]
        
        if TORCH_AVAILABLE:
            self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create a new one."""
        try:
            if os.path.exists(self.model_path):
                self.model = LSTMModel(
                    input_size=self.input_size,
                    hidden_size=self.hidden_size,
                    num_layers=self.num_layers
                )
                self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                self.model.to(self.device)
                self.model.eval()
                logger.info("Loaded existing LSTM model")
            else:
                self._create_new_model()
        except Exception as e:
            logger.warning(f"Error loading LSTM model: {e}. Creating new model.")
            self._create_new_model()
    
    def _create_new_model(self):
        """Create a new LSTM model."""
        self.model = LSTMModel(
            input_size=self.input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers
        )
        self.model.to(self.device)
        logger.info("Created new LSTM model")
    
    def prepare_sequences(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare sequences for LSTM training/inference.
        
        Args:
            data: List of network log dictionaries (sorted by time)
            
        Returns:
            Tuple of (sequences, targets)
        """
        # Extract features
        features = []
        for record in data:
            timestamp = record.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            hour = timestamp.hour
            # Cyclical encoding for hour
            hour_sin = np.sin(2 * np.pi * hour / 24)
            hour_cos = np.cos(2 * np.pi * hour / 24)
            
            feature_vector = [
                record.get('download_speed', 0) / 100,  # Normalize
                record.get('upload_speed', 0) / 100,
                record.get('latency', 0) / 100,
                hour_sin,
                hour_cos
            ]
            features.append(feature_vector)
        
        features = np.array(features)
        
        # Create sequences
        sequences = []
        targets = []
        
        for i in range(len(features) - self.sequence_length):
            seq = features[i:i + self.sequence_length]
            target = features[i + self.sequence_length, 0]  # Predict download speed
            sequences.append(seq)
            targets.append(target)
        
        return np.array(sequences), np.array(targets)
    
    def train(self, data: List[Dict], epochs: int = 50, batch_size: int = 32) -> Dict:
        """
        Train the LSTM model.
        
        Args:
            data: List of network log dictionaries (sorted by time)
            epochs: Number of training epochs
            batch_size: Batch size for training
            
        Returns:
            Training metrics
        """
        if not TORCH_AVAILABLE:
            return {"error": "PyTorch not available"}
        
        logger.info(f"Training LSTM with {len(data)} samples")
        
        X, y = self.prepare_sequences(data)
        
        if len(X) < batch_size:
            return {"error": "Not enough data for training"}
        
        # Convert to tensors
        X_tensor = torch.FloatTensor(X).to(self.device)
        y_tensor = torch.FloatTensor(y).unsqueeze(1).to(self.device)
        
        # Create data loader
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Training setup
        self.model.train()
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5)
        
        losses = []
        for epoch in range(epochs):
            epoch_loss = 0
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(dataloader)
            losses.append(avg_loss)
            scheduler.step(avg_loss)
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.6f}")
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save(self.model.state_dict(), self.model_path)
        
        self.model.eval()
        logger.info("LSTM model trained and saved")
        
        return {
            "samples_trained": len(data),
            "sequences_created": len(X),
            "final_loss": float(losses[-1]),
            "epochs": epochs
        }
    
    def analyze_patterns(self, data: List[Dict]) -> Dict:
        """
        Analyze time series patterns in network data.
        
        Args:
            data: List of network log dictionaries (sorted by time)
            
        Returns:
            Pattern analysis results
        """
        if len(data) < self.sequence_length:
            return {"error": "Not enough data for pattern analysis"}
        
        # Group by hour to find hourly patterns
        hourly_speeds = {i: [] for i in range(24)}
        for record in data:
            timestamp = record.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            hour = timestamp.hour
            hourly_speeds[hour].append(record.get('download_speed', 0))
        
        # Calculate hourly averages
        hourly_avg = {
            hour: np.mean(speeds) if speeds else 0
            for hour, speeds in hourly_speeds.items()
        }
        
        # Find peak and low hours
        sorted_hours = sorted(hourly_avg.items(), key=lambda x: x[1])
        worst_hours = [h for h, _ in sorted_hours[:3]]
        best_hours = [h for h, _ in sorted_hours[-3:]]
        
        # Calculate overall statistics
        all_speeds = [r.get('download_speed', 0) for r in data]
        avg_speed = np.mean(all_speeds)
        std_speed = np.std(all_speeds)
        
        # Detect recurring patterns
        patterns = []
        
        # Check for peak hour degradation
        peak_hours = [18, 19, 20, 21, 22]
        peak_avg = np.mean([hourly_avg.get(h, 0) for h in peak_hours])
        off_peak_avg = np.mean([hourly_avg.get(h, 0) for h in range(24) if h not in peak_hours])
        
        if off_peak_avg > 0 and peak_avg < off_peak_avg * 0.8:
            patterns.append({
                "type": "peak_hour_degradation",
                "description": "Significant speed reduction during peak hours (6-10 PM)",
                "severity": (off_peak_avg - peak_avg) / off_peak_avg,
                "affected_hours": peak_hours
            })
        
        # Check for night-time throttling
        night_hours = [0, 1, 2, 3, 4, 5]
        night_avg = np.mean([hourly_avg.get(h, 0) for h in night_hours])
        day_avg = np.mean([hourly_avg.get(h, 0) for h in range(6, 24)])
        
        if day_avg > 0 and night_avg < day_avg * 0.7:
            patterns.append({
                "type": "night_throttling",
                "description": "Speed reduction during night hours",
                "severity": (day_avg - night_avg) / day_avg,
                "affected_hours": night_hours
            })
        
        return {
            "hourly_averages": hourly_avg,
            "worst_hours": worst_hours,
            "best_hours": best_hours,
            "average_speed": float(avg_speed),
            "speed_std": float(std_speed),
            "patterns_detected": patterns,
            "data_points_analyzed": len(data)
        }
    
    def predict_next(self, data: List[Dict], steps: int = 1) -> List[Dict]:
        """
        Predict future network performance.
        
        Args:
            data: Recent network log dictionaries (at least sequence_length)
            steps: Number of future steps to predict
            
        Returns:
            List of predictions
        """
        if not TORCH_AVAILABLE:
            return [{"error": "PyTorch not available"}]
        
        if len(data) < self.sequence_length:
            return [{"error": f"Need at least {self.sequence_length} data points"}]
        
        self.model.eval()
        predictions = []
        
        # Use the last sequence_length points
        recent_data = data[-self.sequence_length:]
        X, _ = self.prepare_sequences(recent_data + [recent_data[-1]])  # Pad to create one sequence
        
        if len(X) == 0:
            return [{"error": "Could not create sequence"}]
        
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X[-1:]).to(self.device)
            
            for step in range(steps):
                pred = self.model(X_tensor)
                pred_speed = float(pred[0, 0].cpu().numpy()) * 100  # Denormalize
                
                last_timestamp = data[-1].get('timestamp', datetime.now())
                if isinstance(last_timestamp, str):
                    last_timestamp = datetime.fromisoformat(last_timestamp)
                
                pred_timestamp = last_timestamp + timedelta(hours=step + 1)
                
                predictions.append({
                    "step": step + 1,
                    "predicted_download_speed": pred_speed,
                    "timestamp": pred_timestamp.isoformat(),
                    "confidence": 0.8 - (step * 0.1)  # Confidence decreases with steps
                })
        
        return predictions
    
    def detect_sequence_anomalies(self, data: List[Dict]) -> List[Dict]:
        """
        Detect anomalous sequences using prediction error.
        
        Args:
            data: List of network log dictionaries
            
        Returns:
            List of detected anomalies
        """
        if not TORCH_AVAILABLE or len(data) < self.sequence_length + 1:
            return []
        
        self.model.eval()
        X, y = self.prepare_sequences(data)
        
        if len(X) == 0:
            return []
        
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(self.device)
            predictions = self.model(X_tensor).cpu().numpy().flatten()
        
        # Calculate prediction errors
        errors = np.abs(predictions - y)
        error_threshold = np.mean(errors) + 2 * np.std(errors)
        
        anomalies = []
        for i, error in enumerate(errors):
            if error > error_threshold:
                idx = i + self.sequence_length
                anomalies.append({
                    "index": idx,
                    "timestamp": data[idx].get('timestamp'),
                    "predicted_speed": float(predictions[i]) * 100,
                    "actual_speed": float(y[i]) * 100,
                    "error": float(error) * 100,
                    "is_anomaly": True
                })
        
        return anomalies
