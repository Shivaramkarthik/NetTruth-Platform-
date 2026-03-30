"""Privacy and data anonymization service."""
import hashlib
import secrets
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
from loguru import logger

from app.config import settings


class PrivacyService:
    """
    Service for data anonymization and privacy protection.
    
    Implements:
    - Data anonymization
    - Differential privacy
    - Secure hashing
    - PII removal
    """
    
    def __init__(self):
        """Initialize the privacy service."""
        self.salt = settings.ANONYMIZATION_SALT
        self.epsilon = settings.DIFFERENTIAL_PRIVACY_EPSILON
    
    def anonymize_user_id(self, user_id: int) -> str:
        """
        Create an anonymous identifier for a user.
        
        Args:
            user_id: Original user ID
            
        Returns:
            Anonymized identifier (SHA-256 hash)
        """
        # Combine user_id with salt and hash
        data = f"{user_id}:{self.salt}:{datetime.utcnow().strftime('%Y-%m')}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def anonymize_ip(self, ip_address: str) -> str:
        """
        Anonymize an IP address.
        
        Args:
            ip_address: Original IP address
            
        Returns:
            Anonymized IP (hashed)
        """
        # Hash the IP with salt
        data = f"{ip_address}:{self.salt}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def truncate_geohash(self, geohash: str, precision: int = 4) -> str:
        """
        Truncate geohash for privacy (reduces location precision).
        
        Args:
            geohash: Full geohash string
            precision: Number of characters to keep (lower = less precise)
            
        Returns:
            Truncated geohash
        """
        if not geohash:
            return ""
        return geohash[:precision]
    
    def add_differential_privacy_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """
        Add Laplacian noise for differential privacy.
        
        Args:
            value: Original value
            sensitivity: Query sensitivity
            
        Returns:
            Value with added noise
        """
        # Laplace mechanism
        scale = sensitivity / self.epsilon
        noise = np.random.laplace(0, scale)
        return value + noise
    
    def anonymize_speed_data(self, speeds: List[float]) -> Dict[str, float]:
        """
        Anonymize speed data with differential privacy.
        
        Args:
            speeds: List of speed measurements
            
        Returns:
            Anonymized statistics
        """
        if not speeds:
            return {"avg": 0, "min": 0, "max": 0}
        
        # Calculate statistics
        avg_speed = np.mean(speeds)
        min_speed = np.min(speeds)
        max_speed = np.max(speeds)
        
        # Add differential privacy noise
        # Sensitivity for average is range/n
        sensitivity = (max_speed - min_speed) / len(speeds) if len(speeds) > 0 else 1
        
        return {
            "avg": max(0, self.add_differential_privacy_noise(avg_speed, sensitivity)),
            "min": max(0, self.add_differential_privacy_noise(min_speed, sensitivity)),
            "max": max(0, self.add_differential_privacy_noise(max_speed, sensitivity))
        }
    
    def anonymize_user_data(self, user_id: int, logs: List, events: List,
                            geohash: str, isp_name: str) -> Dict[str, Any]:
        """
        Anonymize user data for crowdsourced contribution.
        
        Args:
            user_id: User ID
            logs: List of NetworkLog objects
            events: List of ThrottlingEvent objects
            geohash: User's geohash
            isp_name: ISP name
            
        Returns:
            Anonymized data dictionary
        """
        # Create anonymous ID
        anonymous_id = self.anonymize_user_id(user_id)
        
        # Truncate geohash for privacy
        truncated_geohash = self.truncate_geohash(geohash, precision=4)
        
        # Extract and anonymize speed data
        download_speeds = [log.download_speed for log in logs if log.download_speed]
        upload_speeds = [log.upload_speed for log in logs if log.upload_speed]
        latencies = [log.ping for log in logs if log.ping]
        
        anonymized_download = self.anonymize_speed_data(download_speeds)
        anonymized_upload = self.anonymize_speed_data(upload_speeds)
        anonymized_latency = self.anonymize_speed_data(latencies)
        
        # Calculate compliance rate
        promised_speeds = [log.promised_download for log in logs if log.promised_download]
        if promised_speeds and download_speeds:
            promised = np.mean(promised_speeds)
            compliant = sum(1 for s in download_speeds if s >= promised * 0.8)
            compliance_rate = compliant / len(download_speeds)
        else:
            compliance_rate = 1.0
        
        # Throttling statistics
        throttling_frequency = len(events) / max(1, len(logs)) if logs else 0
        
        if events:
            throttling_severities = [
                e.speed_reduction_percent for e in events 
                if e.speed_reduction_percent
            ]
            throttling_severity = np.mean(throttling_severities) if throttling_severities else 0
            
            # Most common throttling type
            type_counts = {}
            for e in events:
                t = e.throttling_type or "unknown"
                type_counts[t] = type_counts.get(t, 0) + 1
            common_type = max(type_counts, key=type_counts.get) if type_counts else "none"
            
            # Affected services
            all_services = []
            for e in events:
                if e.affected_services:
                    all_services.extend(e.affected_services)
            affected_services = list(set(all_services))[:5]  # Top 5
        else:
            throttling_severity = 0
            common_type = "none"
            affected_services = []
        
        # Calculate peak hour degradation
        peak_speeds = [log.download_speed for log in logs 
                       if log.timestamp and 18 <= log.timestamp.hour <= 22]
        off_peak_speeds = [log.download_speed for log in logs 
                          if log.timestamp and not (18 <= log.timestamp.hour <= 22)]
        
        if peak_speeds and off_peak_speeds:
            peak_avg = np.mean(peak_speeds)
            off_peak_avg = np.mean(off_peak_speeds)
            peak_degradation = (off_peak_avg - peak_avg) / off_peak_avg if off_peak_avg > 0 else 0
        else:
            peak_degradation = 0
        
        # Calculate scores
        speed_score = min(100, (anonymized_download["avg"] / 100) * 100)  # Assuming 100 Mbps as baseline
        reliability_score = max(0, 100 - (throttling_frequency * 200))
        overall_score = (speed_score * 0.5 + reliability_score * 0.5)
        
        return {
            "anonymous_id": anonymous_id,
            "geohash": truncated_geohash,
            "isp_name": isp_name,  # ISP name is not PII
            "avg_download": round(anonymized_download["avg"], 2),
            "avg_upload": round(anonymized_upload["avg"], 2),
            "avg_latency": round(anonymized_latency["avg"], 2),
            "compliance_rate": round(compliance_rate, 3),
            "throttling_frequency": round(throttling_frequency, 3),
            "throttling_severity": round(throttling_severity, 2),
            "common_throttling_type": common_type,
            "affected_services": affected_services,
            "peak_hour_degradation": round(peak_degradation, 3),
            "overall_score": round(overall_score, 1),
            "reliability_score": round(reliability_score, 1),
            "speed_score": round(speed_score, 1),
            "sample_count": len(logs)
        }
    
    def remove_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove personally identifiable information from data.
        
        Args:
            data: Dictionary potentially containing PII
            
        Returns:
            Dictionary with PII removed
        """
        pii_fields = [
            "email", "phone", "name", "full_name", "address",
            "ip_address", "external_ip", "user_id", "account_number",
            "password", "ssn", "credit_card"
        ]
        
        cleaned = {}
        for key, value in data.items():
            if key.lower() in pii_fields:
                continue
            if isinstance(value, dict):
                cleaned[key] = self.remove_pii(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self.remove_pii(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
        
        return cleaned
    
    def generate_consent_token(self, user_id: int) -> str:
        """
        Generate a consent token for data sharing.
        
        Args:
            user_id: User ID
            
        Returns:
            Consent token
        """
        random_bytes = secrets.token_bytes(16)
        data = f"{user_id}:{random_bytes.hex()}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def validate_data_minimization(self, data: Dict[str, Any], 
                                    required_fields: List[str]) -> Dict[str, Any]:
        """
        Apply data minimization - only keep required fields.
        
        Args:
            data: Full data dictionary
            required_fields: List of fields that are actually needed
            
        Returns:
            Minimized data dictionary
        """
        return {k: v for k, v in data.items() if k in required_fields}
