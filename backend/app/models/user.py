"""User model for NetTruth."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.database import Base


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255))
    
    # ISP Information
    isp_name = Column(String(255))
    promised_download_speed = Column(Float)  # Mbps
    promised_upload_speed = Column(Float)  # Mbps
    plan_name = Column(String(255))
    
    # Location (anonymized)
    geohash = Column(String(12))  # For crowdsourced data
    city = Column(String(100))
    country = Column(String(100))
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Privacy settings
    share_anonymous_data = Column(Boolean, default=True)
    
    # Relationships
    network_logs = relationship("NetworkLog", back_populates="user")
    throttling_events = relationship("ThrottlingEvent", back_populates="user")
    reports = relationship("Report", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
