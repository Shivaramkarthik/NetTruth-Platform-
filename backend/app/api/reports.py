"""Legal report generation API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import io

from app.models.database import get_db
from app.models.user import User
from app.models.network_log import NetworkLog
from app.models.throttling_event import ThrottlingEvent
from app.models.report import Report, ReportStatus, ReportType
from app.api.users import get_current_user
from app.services.report_generator import ReportGenerator
from app.ml.prediction_engine import PredictionEngine

router = APIRouter()
report_generator = ReportGenerator()
prediction_engine = PredictionEngine()


# Pydantic models
class ReportRequest(BaseModel):
    report_type: str = "legal_complaint"
    period_days: int = 30
    title: Optional[str] = None
    include_graphs: bool = True
    regulatory_body: Optional[str] = "TRAI"


class ReportResponse(BaseModel):
    id: int
    report_type: str
    title: str
    status: str
    period_start: datetime
    period_end: datetime
    isp_name: Optional[str]
    summary: Optional[dict] = None # Alias for frontend
    summary_stats: Optional[dict] = None
    ai_analysis: Optional[str] = None
    download_url: Optional[str] = None # For frontend
    pdf_filename: Optional[str] = None
    created_at: datetime
    generated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# Endpoints
@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    background_tasks: BackgroundTasks,
    request: ReportRequest = ReportRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a legal complaint report.
    """
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=request.period_days)
    
    # Handle shorthand from frontend
    report_type = request.report_type
    if report_type == "legal":
        report_type = ReportType.LEGAL_COMPLAINT.value
    
    # Create report record
    title = request.title or f"Network Performance Report - {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}"
    
    report = Report(
        user_id=current_user.id,
        report_type=report_type,
        title=title,
        status=ReportStatus.PENDING,
        period_start=period_start,
        period_end=period_end,
        isp_name=current_user.isp_name,
        plan_name=current_user.plan_name,
        promised_speed=f"{current_user.promised_download_speed}/{current_user.promised_upload_speed} Mbps" if current_user.promised_download_speed else None,
        regulatory_body=request.regulatory_body
    )
    
    db.add(report)
    await db.commit()
    await db.refresh(report)
    
    # Set helper fields for response
    report.summary = report.summary_stats or {}
    report.download_url = f"/api/v1/reports/{report.id}/download"
    
    return report


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    report_type: Optional[str] = None,
    status: Optional[str] = None
):
    """
    List all reports for the current user.
    """
    query = select(Report).where(Report.user_id == current_user.id)
    
    if report_type:
        query = query.where(Report.report_type == report_type)
    if status:
        query = query.where(Report.status == status)
    
    query = query.order_by(Report.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific report.
    """
    query = select(Report).where(
        and_(
            Report.id == report_id,
            Report.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download the PDF report.
    """
    query = select(Report).where(
        and_(
            Report.id == report_id,
            Report.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Report is not ready for download")
    
    if not report.pdf_data:
        raise HTTPException(status_code=404, detail="PDF not available")
    
    return StreamingResponse(
        io.BytesIO(report.pdf_data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={report.pdf_filename or 'report.pdf'}"
        }
    )


@router.get("/{report_id}/preview")
async def preview_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get report content for preview (HTML/Markdown).
    """
    query = select(Report).where(
        and_(
            Report.id == report_id,
            Report.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": report.id,
        "title": report.title,
        "content": report.report_content,
        "summary_stats": report.summary_stats,
        "ai_analysis": report.ai_analysis,
        "ai_recommendations": report.ai_recommendations
    }


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a report.
    """
    query = select(Report).where(
        and_(
            Report.id == report_id,
            Report.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    await db.delete(report)
    await db.commit()
    
    return {"message": "Report deleted successfully"}


@router.post("/generate-complaint-email")
async def generate_complaint_email(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a complaint email template based on the report.
    """
    query = select(Report).where(
        and_(
            Report.id == report_id,
            Report.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Generate email template
    email_template = report_generator.generate_complaint_email(
        user_name=current_user.full_name or "Customer",
        isp_name=report.isp_name or "ISP",
        plan_name=report.plan_name,
        summary_stats=report.summary_stats,
        ai_analysis=report.ai_analysis,
        period_start=report.period_start,
        period_end=report.period_end
    )
    
    return {
        "subject": email_template["subject"],
        "body": email_template["body"],
        "suggested_recipients": email_template.get("recipients", [])
    }


@router.get("/templates/trai-complaint")
async def get_trai_complaint_template(
    current_user: User = Depends(get_current_user)
):
    """
    Get TRAI complaint template format.
    """
    return report_generator.get_trai_template()


async def generate_report_task(
    report_id: int,
    user_id: int,
    period_start: datetime,
    period_end: datetime,
    include_graphs: bool
):
    """
    Background task to generate the full report.
    """
    from app.models.database import async_session
    
    async with async_session() as db:
        # Get report
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        
        if not report:
            return
        
        try:
            report.status = ReportStatus.GENERATING
            await db.commit()
            
            # Get network logs
            logs_result = await db.execute(
                select(NetworkLog).where(
                    and_(
                        NetworkLog.user_id == user_id,
                        NetworkLog.timestamp >= period_start,
                        NetworkLog.timestamp <= period_end
                    )
                ).order_by(NetworkLog.timestamp)
            )
            logs = logs_result.scalars().all()
            
            # Get throttling events
            events_result = await db.execute(
                select(ThrottlingEvent).where(
                    and_(
                        ThrottlingEvent.user_id == user_id,
                        ThrottlingEvent.detected_at >= period_start,
                        ThrottlingEvent.detected_at <= period_end
                    )
                )
            )
            events = events_result.scalars().all()
            
            # Get user
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one()
            
            # Generate evidence using ML
            data = [log.to_dict() for log in logs]
            evidence = prediction_engine.get_throttling_evidence(data) if data else {}
            
            # Generate report content
            report_content = report_generator.generate_report_content(
                user=user,
                logs=logs,
                events=events,
                evidence=evidence,
                period_start=period_start,
                period_end=period_end
            )
            
            # Generate PDF
            pdf_data = report_generator.generate_pdf(
                content=report_content,
                include_graphs=include_graphs
            )
            
            # Update report
            report.report_content = report_content["html"]
            report.summary_stats = evidence.get("speed_statistics", {})
            report.ai_analysis = evidence.get("summary", {}).get("status_message", "")
            report.ai_recommendations = evidence.get("throttling_evidence", {})
            report.pdf_data = pdf_data
            report.pdf_filename = f"nettruth_report_{report_id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
            report.status = ReportStatus.COMPLETED
            report.generated_at = datetime.utcnow()
            
            await db.commit()
            
        except Exception as e:
            report.status = ReportStatus.FAILED
            await db.commit()
            raise e
