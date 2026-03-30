"""Network log model for storing speed test results."""
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.database import Base


class NetworkLog(Base):
    """Network performance log entry."""
    __tablename__ = "network_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Speed measurements (Mbps)
    download_speed = Column(Float, nullable=False)
    upload_speed = Column(Float, nullable=False)
    
    # Latency measurements (ms)
    ping = Column(Float, nullable=False)
    jitter = Column(Float)
    packet_loss = Column(Float)  # Percentage
    
    # Server information
    test_server = Column(String(255))
    server_location = Column(String(255))
    
    # ISP information at time of test
    isp_name = Column(String(255))
    external_ip = Column(String(45))  # Anonymized/hashed
    
    # Promised vs actual comparison
    promised_download = Column(Float)
    promised_upload = Column(Float)
    download_ratio = Column(Float)  # actual/promised
    upload_ratio = Column(Float)  # actual/promised
    
    # Context
    test_type = Column(String(50), default="automatic")  # automatic, manual, app-specific
    target_service = Column(String(100))  # e.g., "YouTube", "Netflix", "general"
    
    # Additional metadata
    extra_data = Column(JSON)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="network_logs")
    
    def __repr__(self):
        return f"<NetworkLog(id={self.id}, download={self.download_speed}Mbps, timestamp={self.timestamp})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "download_speed": self.download_speed,
            "upload_speed": self.upload_speed,
            "ping": self.ping,
            "jitter": self.jitter,
            "packet_loss": self.packet_loss,
            "download_ratio": self.download_ratio,
            "upload_ratio": self.upload_ratio,
            "target_service": self.target_service,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
