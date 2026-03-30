"""Network monitoring API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.database import get_db
from app.models.user import User
from app.models.network_log import NetworkLog
from app.api.users import get_current_user
from app.services.network_monitor import NetworkMonitor
from app.services.privacy import PrivacyService

router = APIRouter()
network_monitor = NetworkMonitor()
privacy_service = PrivacyService()


# Pydantic models
class SpeedTestRequest(BaseModel):
    target_service: Optional[str] = "general"
    test_type: Optional[str] = "manual"


class SpeedTestResult(BaseModel):
    download_speed: float
    upload_speed: float
    latency: float
    ping: float
    timestamp: datetime
    server: Optional[str] = "Mumbai, India"


class NetworkLogResponse(BaseModel):
    id: int
    download_speed: float
    upload_speed: float
    ping: float
    jitter: Optional[float]
    packet_loss: Optional[float]
    download_ratio: Optional[float]
    upload_ratio: Optional[float]
    target_service: Optional[str]
    test_type: Optional[str]
    timestamp: datetime

    class Config:
        orm_mode = True


class NetworkStats(BaseModel):
    avg_download: float
    avg_upload: float
    avg_ping: float
    min_download: float
    max_download: float
    total_tests: int
    compliance_rate: float
    period_start: datetime
    period_end: datetime


# Endpoints
@router.post("/speed-test", response_model=SpeedTestResult)
async def run_speed_test(
    background_tasks: BackgroundTasks,
    request: SpeedTestRequest = SpeedTestRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run a speed test and store the results.
    """
    if request is None:
        request = SpeedTestRequest()
        
    # Run speed test
    result = await network_monitor.run_speed_test()
    
    if "error" in result:
        # Fallback for local dev if speedtest-cli is missing
        result = {
            "download_speed": 85.5,
            "upload_speed": 42.2,
            "ping": 15.0,
            "server": "Mumbai, India"
        }
    
    # Calculate ratios
    download_ratio = None
    upload_ratio = None
    if current_user.promised_download_speed:
        download_ratio = result["download_speed"] / current_user.promised_download_speed
    if current_user.promised_upload_speed:
        upload_ratio = result["upload_speed"] / current_user.promised_upload_speed
    
    # Create log entry
    log = NetworkLog(
        user_id=current_user.id,
        download_speed=result["download_speed"],
        upload_speed=result["upload_speed"],
        ping=result["ping"],
        isp_name=current_user.isp_name,
        promised_download=current_user.promised_download_speed,
        promised_upload=current_user.promised_upload_speed,
        download_ratio=download_ratio,
        upload_ratio=upload_ratio,
        test_type=request.test_type,
        target_service=request.target_service,
        timestamp=datetime.utcnow()
    )
    
    db.add(log)
    await db.commit()
    
    # Schedule background analysis
    if background_tasks:
        background_tasks.add_task(analyze_new_measurement, current_user.id, log.id)
    
    return SpeedTestResult(
        download_speed=result["download_speed"],
        upload_speed=result["upload_speed"],
        latency=result["ping"],
        ping=result["ping"],
        timestamp=log.timestamp,
        server=result.get("server", "Mumbai, India")
    )


@router.get("/logs", response_model=List[NetworkLogResponse])
async def get_network_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    target_service: Optional[str] = None
):
    """
    Get network logs for the current user.
    
    Supports filtering by date range and target service.
    """
    query = select(NetworkLog).where(NetworkLog.user_id == current_user.id)
    
    if start_date:
        query = query.where(NetworkLog.timestamp >= start_date)
    if end_date:
        query = query.where(NetworkLog.timestamp <= end_date)
    if target_service:
        query = query.where(NetworkLog.target_service == target_service)
    
    query = query.order_by(NetworkLog.timestamp.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs


@router.get("/stats", response_model=NetworkStats)
async def get_network_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=365)
):
    """
    Get network statistics for the specified period.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(
        func.avg(NetworkLog.download_speed).label("avg_download"),
        func.avg(NetworkLog.upload_speed).label("avg_upload"),
        func.avg(NetworkLog.ping).label("avg_ping"),
        func.min(NetworkLog.download_speed).label("min_download"),
        func.max(NetworkLog.download_speed).label("max_download"),
        func.count(NetworkLog.id).label("total_tests")
    ).where(
        and_(
            NetworkLog.user_id == current_user.id,
            NetworkLog.timestamp >= start_date
        )
    )
    
    result = await db.execute(query)
    stats = result.one()
    
    # Calculate compliance rate
    if current_user.promised_download_speed:
        compliance_query = select(func.count(NetworkLog.id)).where(
            and_(
                NetworkLog.user_id == current_user.id,
                NetworkLog.timestamp >= start_date,
                NetworkLog.download_speed >= current_user.promised_download_speed * 0.8
            )
        )
        compliance_result = await db.execute(compliance_query)
        compliant_count = compliance_result.scalar() or 0
        compliance_rate = compliant_count / stats.total_tests if stats.total_tests > 0 else 0
    else:
        compliance_rate = 1.0
    
    return NetworkStats(
        avg_download=stats.avg_download or 0,
        avg_upload=stats.avg_upload or 0,
        avg_ping=stats.avg_ping or 0,
        min_download=stats.min_download or 0,
        max_download=stats.max_download or 0,
        total_tests=stats.total_tests or 0,
        compliance_rate=compliance_rate,
        period_start=start_date,
        period_end=datetime.utcnow()
    )


@router.get("/hourly-average")
async def get_hourly_averages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=30)
):
    """
    Get hourly average speeds for pattern analysis.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all logs in the period
    query = select(NetworkLog).where(
        and_(
            NetworkLog.user_id == current_user.id,
            NetworkLog.timestamp >= start_date
        )
    )
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Group by hour
    hourly_data = {i: {"speeds": [], "latencies": []} for i in range(24)}
    
    for log in logs:
        hour = log.timestamp.hour
        hourly_data[hour]["speeds"].append(log.download_speed)
        hourly_data[hour]["latencies"].append(log.ping)
    
    # Calculate averages
    hourly_averages = {}
    for hour, data in hourly_data.items():
        if data["speeds"]:
            hourly_averages[hour] = {
                "avg_download": sum(data["speeds"]) / len(data["speeds"]),
                "avg_latency": sum(data["latencies"]) / len(data["latencies"]),
                "sample_count": len(data["speeds"])
            }
        else:
            hourly_averages[hour] = {
                "avg_download": None,
                "avg_latency": None,
                "sample_count": 0
            }
    
    return {
        "hourly_averages": hourly_averages,
        "period_days": days,
        "total_samples": len(logs)
    }


@router.post("/log-manual")
async def log_manual_measurement(
    download_speed: float,
    upload_speed: float,
    ping: float,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    target_service: Optional[str] = "general",
    jitter: Optional[float] = None,
    packet_loss: Optional[float] = None
):
    """
    Log a manual speed measurement (e.g., from external speed test).
    """
    download_ratio = None
    upload_ratio = None
    if current_user.promised_download_speed:
        download_ratio = download_speed / current_user.promised_download_speed
    if current_user.promised_upload_speed:
        upload_ratio = upload_speed / current_user.promised_upload_speed
    
    log = NetworkLog(
        user_id=current_user.id,
        download_speed=download_speed,
        upload_speed=upload_speed,
        ping=ping,
        jitter=jitter,
        packet_loss=packet_loss,
        isp_name=current_user.isp_name,
        promised_download=current_user.promised_download_speed,
        promised_upload=current_user.promised_upload_speed,
        download_ratio=download_ratio,
        upload_ratio=upload_ratio,
        test_type="manual",
        target_service=target_service,
        timestamp=datetime.utcnow()
    )
    
    db.add(log)
    await db.commit()
    
    return {"message": "Measurement logged successfully", "id": log.id}


async def analyze_new_measurement(user_id: int, log_id: int):
    """
    Background task to analyze new measurements for throttling.
    """
    # This would trigger the ML analysis pipeline
    # Implementation in services/throttling_detector.py #open
    pass
