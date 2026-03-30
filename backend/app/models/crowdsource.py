"""Crowdsourced data model for anonymized network intelligence."""
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, Index
from datetime import datetime

from app.models.database import Base


class CrowdsourceData(Base):
    """Anonymized crowdsourced network data."""
    __tablename__ = "crowdsource_data"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Anonymized user identifier (hashed)
    anonymous_id = Column(String(64), index=True)
    
    # Location (geohash for privacy)
    geohash = Column(String(12), index=True)  # Precision level for privacy
    city = Column(String(100))
    region = Column(String(100))
    country = Column(String(100))
    
    # ISP information
    isp_name = Column(String(255), index=True)
    plan_type = Column(String(100))  # e.g., "fiber", "cable", "dsl"
    
    # Aggregated metrics (with differential privacy noise)
    avg_download_speed = Column(Float)
    avg_upload_speed = Column(Float)
    avg_latency = Column(Float)
    
    # Speed compliance
    promised_speed = Column(Float)
    compliance_rate = Column(Float)  # Percentage of time meeting promised speed
    
    # Throttling statistics
    throttling_frequency = Column(Float)  # Events per day
    throttling_severity = Column(Float)  # Average speed reduction
    common_throttling_type = Column(String(50))
    affected_services = Column(JSON)
    
    # Time patterns
    peak_hour_degradation = Column(Float)  # Speed reduction during peak hours
    worst_hours = Column(JSON)  # Hours with worst performance
    
    # Quality scores (0-100)
    overall_score = Column(Float)
    reliability_score = Column(Float)
    speed_score = Column(Float)
    latency_score = Column(Float)
    
    # Data quality
    sample_count = Column(Integer)  # Number of measurements
    data_period_days = Column(Integer)
    
    # Timestamps
    aggregated_at = Column(DateTime, default=datetime.utcnow)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_location_isp', 'geohash', 'isp_name'),
        Index('idx_isp_score', 'isp_name', 'overall_score'),
    )
    
    def __repr__(self):
        return f"<CrowdsourceData(id={self.id}, isp={self.isp_name}, geohash={self.geohash})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "geohash": self.geohash,
            "city": self.city,
            "region": self.region,
            "country": self.country,
            "isp_name": self.isp_name,
            "avg_download_speed": self.avg_download_speed,
            "avg_upload_speed": self.avg_upload_speed,
            "avg_latency": self.avg_latency,
            "compliance_rate": self.compliance_rate,
            "throttling_frequency": self.throttling_frequency,
            "overall_score": self.overall_score,
            "reliability_score": self.reliability_score,
            "speed_score": self.speed_score,
            "sample_count": self.sample_count
        }


class ISPRanking(Base):
    """ISP ranking based on crowdsourced data."""
    __tablename__ = "isp_rankings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # ISP identification
    isp_name = Column(String(255), index=True)
    
    # Geographic scope
    scope = Column(String(50))  # "national", "regional", "city"
    region = Column(String(100))
    country = Column(String(100))
    
    # Rankings
    overall_rank = Column(Integer)
    speed_rank = Column(Integer)
    reliability_rank = Column(Integer)
    value_rank = Column(Integer)
    
    # Scores (0-100)
    overall_score = Column(Float)
    speed_score = Column(Float)
    reliability_score = Column(Float)
    transparency_score = Column(Float)
    
    # Statistics
    total_users = Column(Integer)
    total_measurements = Column(Integer)
    avg_throttling_rate = Column(Float)
    
    # Comparison to competitors
    percentile = Column(Float)  # Where this ISP stands among all ISPs
    
    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime)
    
    def __repr__(self):
        return f"<ISPRanking(isp={self.isp_name}, rank={self.overall_rank})>"
