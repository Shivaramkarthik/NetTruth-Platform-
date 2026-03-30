"""Legal report model for generated complaint documents."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.models.database import Base


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportType(str, Enum):
    """Types of reports."""
    LEGAL_COMPLAINT = "legal_complaint"
    EVIDENCE_SUMMARY = "evidence_summary"
    ISP_COMPARISON = "isp_comparison"
    MONTHLY_SUMMARY = "monthly_summary"
    TRAI_COMPLAINT = "trai_complaint"


class Report(Base):
    """Generated legal/evidence report."""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Report metadata
    report_type = Column(String(50), default=ReportType.LEGAL_COMPLAINT)
    title = Column(String(255), nullable=False)
    status = Column(String(50), default=ReportStatus.PENDING)
    
    # Time period covered
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # ISP information
    isp_name = Column(String(255))
    plan_name = Column(String(255))
    promised_speed = Column(String(100))
    
    # Summary statistics
    summary_stats = Column(JSON)
    # Example: {
    #   "avg_download": 45.2,
    #   "avg_upload": 12.5,
    #   "throttling_incidents": 15,
    #   "total_downtime_hours": 3.5,
    #   "speed_compliance_rate": 0.65
    # }
    
    # Throttling events included
    throttling_event_ids = Column(JSON)
    throttling_summary = Column(Text)
    
    # AI analysis
    ai_analysis = Column(Text)
    ai_recommendations = Column(JSON)
    
    # Generated content
    report_content = Column(Text)  # HTML/Markdown content
    pdf_data = Column(LargeBinary)  # Generated PDF
    pdf_filename = Column(String(255))
    
    # Regulatory compliance
    regulatory_body = Column(String(100))  # e.g., "TRAI"
    compliance_format = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    generated_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="reports")
    
    def __repr__(self):
        return f"<Report(id={self.id}, type={self.report_type}, status={self.status})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "report_type": self.report_type,
            "title": self.title,
            "status": self.status,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "isp_name": self.isp_name,
            "summary_stats": self.summary_stats,
            "ai_analysis": self.ai_analysis,
            "pdf_filename": self.pdf_filename,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }
