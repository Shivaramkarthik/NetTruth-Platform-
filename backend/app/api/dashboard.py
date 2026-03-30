"""Dashboard API endpoints."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.database import get_db
from app.models.user import User
from app.models.network_log import NetworkLog
from app.models.throttling_event import ThrottlingEvent
from app.models.report import Report
from app.api.users import get_current_user

router = APIRouter()


# Pydantic models
class DashboardSummary(BaseModel):
    current_speed: Dict[str, float]
    promised_speed: float
    speed_delivery_rate: float
    throttling_status: Dict[str, Any]
    alerts: List[Dict[str, Any]]


class SpeedTrend(BaseModel):
    timestamp: datetime
    download_speed: float
    upload_speed: float
    latency: float


class ISPRating(BaseModel):
    overall_score: float
    speed_score: float
    reliability_score: float
    value_score: float
    comparison_to_area: str


# Endpoints
@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard summary with key metrics and alerts.
    """
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    # Get last speed test
    last_test_result = await db.execute(
        select(NetworkLog)
        .where(NetworkLog.user_id == current_user.id)
        .order_by(NetworkLog.timestamp.desc())
        .limit(1)
    )
    last_test = last_test_result.scalar_one_or_none()
    
    # Get 24h averages
    avg_24h_result = await db.execute(
        select(
            func.avg(NetworkLog.download_speed).label("avg_download"),
            func.avg(NetworkLog.upload_speed).label("avg_upload"),
            func.avg(NetworkLog.ping).label("avg_latency")
        ).where(
            and_(
                NetworkLog.user_id == current_user.id,
                NetworkLog.timestamp >= day_ago
            )
        )
    )
    avg_24h = avg_24h_result.one()
    
    # Get throttling events count
    throttling_24h_result = await db.execute(
        select(func.count(ThrottlingEvent.id)).where(
            and_(
                ThrottlingEvent.user_id == current_user.id,
                ThrottlingEvent.detected_at >= day_ago
            )
        )
    )
    throttling_24h = throttling_24h_result.scalar() or 0
    
    throttling_7d_result = await db.execute(
        select(func.count(ThrottlingEvent.id)).where(
            and_(
                ThrottlingEvent.user_id == current_user.id,
                ThrottlingEvent.detected_at >= week_ago
            )
        )
    )
    throttling_7d = throttling_7d_result.scalar() or 0
    
    # Get 7d test count and compliance
    tests_7d_result = await db.execute(
        select(func.count(NetworkLog.id)).where(
            and_(
                NetworkLog.user_id == current_user.id,
                NetworkLog.timestamp >= week_ago
            )
        )
    )
    total_tests_7d = tests_7d_result.scalar() or 0
    
    # Calculate compliance rate
    compliance_rate = 1.0
    if current_user.promised_download_speed and total_tests_7d > 0:
        compliant_result = await db.execute(
            select(func.count(NetworkLog.id)).where(
                and_(
                    NetworkLog.user_id == current_user.id,
                    NetworkLog.timestamp >= week_ago,
                    NetworkLog.download_speed >= current_user.promised_download_speed * 0.8
                )
            )
        )
        compliant_count = compliant_result.scalar() or 0
        compliance_rate = compliant_count / total_tests_7d
    
    # Determine current status
    if throttling_24h > 3:
        current_status = "critical"
    elif throttling_24h > 0 or compliance_rate < 0.7:
        current_status = "warning"
    else:
        current_status = "good"
    
    # Generate alerts
    alerts = []
    if throttling_24h > 0:
        alerts.append({
            "type": "throttling",
            "severity": "high" if throttling_24h > 3 else "medium",
            "title": f"⚠️ {throttling_24h} throttling event(s) detected in last 24 hours",
            "action": "View throttling details"
        })
    
    if compliance_rate < 0.8:
        alerts.append({
            "type": "compliance",
            "severity": "medium",
            "title": f"📉 Speed compliance at {compliance_rate*100:.0f}% (below 80% threshold)",
            "action": "Generate report for ISP"
        })
    
    if total_tests_7d < 10:
        alerts.append({
            "type": "data",
            "severity": "low",
            "title": "📊 Limited data available for analysis",
            "action": "Run more speed tests for better insights"
        })
    
    return DashboardSummary(
        current_speed={
            "download": last_test.download_speed if last_test else 0.0,
            "upload": last_test.upload_speed if last_test else 0.0,
            "latency": last_test.ping if last_test else 0.0
        },
        promised_speed=current_user.promised_download_speed or 100.0,
        speed_delivery_rate=compliance_rate,
        throttling_status={
            "active": throttling_24h > 0,
            "last_detected": datetime.utcnow().isoformat() if throttling_24h > 0 else None
        },
        alerts=alerts
    )


@router.get("/speed-trends", response_model=List[SpeedTrend])
async def get_speed_trends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
    interval: str = Query("hour", enum=["hour", "day"])
):
    """
    Get speed trends for graphing.
    """
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(NetworkLog).where(
        and_(
            NetworkLog.user_id == current_user.id,
            NetworkLog.timestamp >= start_time
        )
    ).order_by(NetworkLog.timestamp)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        SpeedTrend(
            timestamp=log.timestamp,
            download_speed=log.download_speed,
            upload_speed=log.upload_speed,
            latency=log.ping
        )
        for log in logs
    ]


@router.get("/isp-rating", response_model=ISPRating)
async def get_isp_rating(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ISP rating based on user's data.
    """
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Get user's stats
    stats_result = await db.execute(
        select(
            func.avg(NetworkLog.download_speed).label("avg_download"),
            func.avg(NetworkLog.upload_speed).label("avg_upload"),
            func.avg(NetworkLog.ping).label("avg_latency"),
            func.count(NetworkLog.id).label("total_tests")
        ).where(
            and_(
                NetworkLog.user_id == current_user.id,
                NetworkLog.timestamp >= week_ago
            )
        )
    )
    stats = stats_result.one()
    
    # Get throttling count
    throttling_result = await db.execute(
        select(func.count(ThrottlingEvent.id)).where(
            and_(
                ThrottlingEvent.user_id == current_user.id,
                ThrottlingEvent.detected_at >= week_ago
            )
        )
    )
    throttling_count = throttling_result.scalar() or 0
    
    # Calculate scores (0-100)
    promised = current_user.promised_download_speed or 100
    
    # Speed score: based on actual vs promised
    speed_ratio = (stats.avg_download or 0) / promised
    speed_score = min(100, speed_ratio * 100)
    
    # Reliability score: based on throttling frequency
    total_tests = stats.total_tests or 1
    throttling_rate = throttling_count / total_tests
    reliability_score = max(0, 100 - (throttling_rate * 200))
    
    # Value score: speed per dollar (simplified)
    value_score = speed_score * 0.8 + reliability_score * 0.2
    
    # Overall score
    overall_score = (speed_score * 0.4 + reliability_score * 0.4 + value_score * 0.2)
    
    # Comparison to area (would use crowdsourced data in production)
    if overall_score >= 80:
        comparison = "above_average"
    elif overall_score >= 60:
        comparison = "average"
    else:
        comparison = "below_average"
    
    return ISPRating(
        overall_score=round(overall_score, 1),
        speed_score=round(speed_score, 1),
        reliability_score=round(reliability_score, 1),
        value_score=round(value_score, 1),
        comparison_to_area=comparison
    )


@router.get("/recent-activity")
async def get_recent_activity(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get recent activity feed.
    """
    activities = []
    
    # Recent speed tests
    tests_result = await db.execute(
        select(NetworkLog)
        .where(NetworkLog.user_id == current_user.id)
        .order_by(NetworkLog.timestamp.desc())
        .limit(limit)
    )
    tests = tests_result.scalars().all()
    
    for test in tests:
        activities.append({
            "type": "speed_test",
            "timestamp": test.timestamp.isoformat(),
            "title": f"Speed test: {test.download_speed:.1f} Mbps down, {test.upload_speed:.1f} Mbps up",
            "details": {
                "download": test.download_speed,
                "upload": test.upload_speed,
                "ping": test.ping
            }
        })
    
    # Recent throttling events
    events_result = await db.execute(
        select(ThrottlingEvent)
        .where(ThrottlingEvent.user_id == current_user.id)
        .order_by(ThrottlingEvent.detected_at.desc())
        .limit(limit)
    )
    events = events_result.scalars().all()
    
    for event in events:
        activities.append({
            "type": "throttling_event",
            "timestamp": event.detected_at.isoformat(),
            "title": f"Throttling detected: {event.throttling_type}",
            "details": {
                "confidence": event.confidence,
                "type": event.throttling_type,
                "affected_services": event.affected_services
            }
        })
    
    # Recent reports
    reports_result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .limit(5)
    )
    reports = reports_result.scalars().all()
    
    for report in reports:
        activities.append({
            "type": "report",
            "timestamp": report.created_at.isoformat(),
            "title": f"Report generated: {report.title}",
            "details": {
                "status": report.status,
                "type": report.report_type
            }
        })
    
    # Sort by timestamp
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return activities[:limit]


@router.get("/widgets")
async def get_dashboard_widgets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get data for dashboard widgets.
    """
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    # Speed gauge data
    last_test_result = await db.execute(
        select(NetworkLog)
        .where(NetworkLog.user_id == current_user.id)
        .order_by(NetworkLog.timestamp.desc())
        .limit(1)
    )
    last_test = last_test_result.scalar_one_or_none()
    
    speed_gauge = {
        "current_download": last_test.download_speed if last_test else 0,
        "current_upload": last_test.upload_speed if last_test else 0,
        "promised_download": current_user.promised_download_speed or 100,
        "promised_upload": current_user.promised_upload_speed or 50,
        "percentage": (last_test.download_speed / (current_user.promised_download_speed or 100) * 100) if last_test else 0
    }
    
    # Throttling pie chart data
    throttling_result = await db.execute(
        select(
            ThrottlingEvent.throttling_type,
            func.count(ThrottlingEvent.id).label("count")
        ).where(
            and_(
                ThrottlingEvent.user_id == current_user.id,
                ThrottlingEvent.detected_at >= week_ago
            )
        ).group_by(ThrottlingEvent.throttling_type)
    )
    throttling_types = throttling_result.all()
    
    throttling_chart = [
        {"type": t.throttling_type, "count": t.count}
        for t in throttling_types
    ]
    
    # Hourly performance data
    hourly_result = await db.execute(
        select(
            func.extract('hour', NetworkLog.timestamp).label("hour"),
            func.avg(NetworkLog.download_speed).label("avg_speed")
        ).where(
            and_(
                NetworkLog.user_id == current_user.id,
                NetworkLog.timestamp >= week_ago
            )
        ).group_by(func.extract('hour', NetworkLog.timestamp))
    )
    hourly_data = hourly_result.all()
    
    hourly_chart = [
        {"hour": int(h.hour), "avg_speed": float(h.avg_speed or 0)}
        for h in hourly_data
    ]
    
    return {
        "speed_gauge": speed_gauge,
        "throttling_chart": throttling_chart,
        "hourly_chart": hourly_chart,
        "isp_info": {
            "name": current_user.isp_name,
            "plan": current_user.plan_name,
            "promised_speed": f"{current_user.promised_download_speed}/{current_user.promised_upload_speed} Mbps"
        }
    }
