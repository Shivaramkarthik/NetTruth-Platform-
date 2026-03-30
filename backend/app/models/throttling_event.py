"""Throttling event model for detected throttling incidents."""
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.models.database import Base


class ThrottlingType(str, Enum):
    """Types of throttling detected."""
    TIME_BASED = "time_based"  # Speed drops at specific times
    APP_SPECIFIC = "app_specific"  # Throttling specific apps/services
    DATA_CAP = "data_cap"  # FUP/data cap throttling
    GENERAL = "general"  # General speed degradation
    PEAK_HOURS = "peak_hours"  # Peak hour throttling
    UNKNOWN = "unknown"


class ThrottlingEvent(Base):
    """Detected throttling event."""
    __tablename__ = "throttling_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Detection results
    throttling_detected = Column(Boolean, default=True)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    throttling_type = Column(String(50), default=ThrottlingType.UNKNOWN)
    
    # Affected services
    affected_services = Column(JSON)  # List of affected services
    
    # Speed comparison
    expected_speed = Column(Float)  # Expected based on plan
    actual_speed = Column(Float)  # Measured speed
    speed_reduction_percent = Column(Float)  # Percentage reduction
    
    # Time context
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer)
    
    # ML model information
    detection_model = Column(String(100))  # Which model detected this
    model_version = Column(String(50))
    raw_prediction = Column(JSON)  # Raw model output
    
    # Evidence
    evidence_summary = Column(Text)
    related_log_ids = Column(JSON)  # IDs of related network logs
    
    # Status
    is_verified = Column(Boolean, default=False)  # User verified
    is_reported = Column(Boolean, default=False)  # Included in report
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="throttling_events")
    
    def __repr__(self):
        return f"<ThrottlingEvent(id={self.id}, type={self.throttling_type}, confidence={self.confidence})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "throttling_detected": self.throttling_detected,
            "confidence": self.confidence,
            "type": self.throttling_type,
            "affected_services": self.affected_services,
            "expected_speed": self.expected_speed,
            "actual_speed": self.actual_speed,
            "speed_reduction_percent": self.speed_reduction_percent,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "detection_model": self.detection_model,
            "evidence_summary": self.evidence_summary,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None
        }
