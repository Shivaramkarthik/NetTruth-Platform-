"""Throttling detection API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.database import get_db
from app.models.user import User
from app.models.network_log import NetworkLog
from app.models.throttling_event import ThrottlingEvent
from app.api.users import get_current_user
from app.ml.prediction_engine import PredictionEngine

router = APIRouter()
prediction_engine = PredictionEngine()


# Pydantic models
class ThrottlingAnalysisRequest(BaseModel):
    days: int = 7
    include_predictions: bool = True


class ThrottlingEventResponse(BaseModel):
    id: int
    throttling_detected: bool
    confidence: float
    throttling_type: str
    affected_services: Optional[List[str]]
    expected_speed: Optional[float]
    actual_speed: Optional[float]
    speed_reduction_percent: Optional[float]
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    evidence_summary: Optional[str]
    detected_at: datetime

    class Config:
        from_attributes = True


class AnalysisResult(BaseModel):
    timestamp: str
    data_points_analyzed: int
    summary: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    anomaly_detection: Dict[str, Any]
    throttling_classification: Dict[str, Any]
    time_series_analysis: Dict[str, Any]


# Endpoints
@router.post("/analyze", response_model=AnalysisResult)
async def analyze_throttling(
    request: ThrottlingAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze network data for throttling patterns.
    
    Uses ML models to detect:
    - Anomalies in network performance
    - Throttling type classification
    - Time-series patterns
    - Future predictions
    """
    start_date = datetime.utcnow() - timedelta(days=request.days)
    
    # Get network logs
    query = select(NetworkLog).where(
        and_(
            NetworkLog.user_id == current_user.id,
            NetworkLog.timestamp >= start_date
        )
    ).order_by(NetworkLog.timestamp)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if not logs:
        raise HTTPException(
            status_code=404,
            detail="No network data found for the specified period"
        )
    
    # Convert to dict format for ML models
    data = [log.to_dict() for log in logs]
    
    # Run analysis
    analysis = prediction_engine.analyze(data, include_predictions=request.include_predictions)
    
    # Store detected throttling events
    if analysis.get('throttling_classification', {}).get('high_confidence_events'):
        background_tasks.add_task(
            store_throttling_events,
            current_user.id,
            analysis['throttling_classification']['high_confidence_events'],
            db
        )
    
    return AnalysisResult(**analysis)


@router.get("/events", response_model=List[ThrottlingEventResponse])
async def get_throttling_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    throttling_type: Optional[str] = None,
    min_confidence: float = Query(0.5, ge=0, le=1)
):
    """
    Get detected throttling events.
    """
    query = select(ThrottlingEvent).where(
        and_(
            ThrottlingEvent.user_id == current_user.id,
            ThrottlingEvent.confidence >= min_confidence
        )
    )
    
    if start_date:
        query = query.where(ThrottlingEvent.detected_at >= start_date)
    if end_date:
        query = query.where(ThrottlingEvent.detected_at <= end_date)
    if throttling_type:
        query = query.where(ThrottlingEvent.throttling_type == throttling_type)
    
    query = query.order_by(ThrottlingEvent.detected_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return events


@router.get("/events/{event_id}", response_model=ThrottlingEventResponse)
async def get_throttling_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific throttling event.
    """
    query = select(ThrottlingEvent).where(
        and_(
            ThrottlingEvent.id == event_id,
            ThrottlingEvent.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Throttling event not found")
    
    return event


@router.post("/events/{event_id}/verify")
async def verify_throttling_event(
    event_id: int,
    verified: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    User verification of a throttling event.
    
    Helps improve ML model accuracy through user feedback.
    """
    query = select(ThrottlingEvent).where(
        and_(
            ThrottlingEvent.id == event_id,
            ThrottlingEvent.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Throttling event not found")
    
    event.is_verified = verified
    await db.commit()
    
    return {"message": "Event verification updated", "verified": verified}


@router.get("/summary")
async def get_throttling_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """
    Get a summary of throttling events.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Count events by type
    query = select(
        ThrottlingEvent.throttling_type,
        func.count(ThrottlingEvent.id).label("count"),
        func.avg(ThrottlingEvent.confidence).label("avg_confidence"),
        func.avg(ThrottlingEvent.speed_reduction_percent).label("avg_reduction")
    ).where(
        and_(
            ThrottlingEvent.user_id == current_user.id,
            ThrottlingEvent.detected_at >= start_date
        )
    ).group_by(ThrottlingEvent.throttling_type)
    
    result = await db.execute(query)
    type_stats = result.all()
    
    # Total events
    total_query = select(func.count(ThrottlingEvent.id)).where(
        and_(
            ThrottlingEvent.user_id == current_user.id,
            ThrottlingEvent.detected_at >= start_date
        )
    )
    total_result = await db.execute(total_query)
    total_events = total_result.scalar() or 0
    
    # Events by day
    daily_query = select(
        func.date(ThrottlingEvent.detected_at).label("date"),
        func.count(ThrottlingEvent.id).label("count")
    ).where(
        and_(
            ThrottlingEvent.user_id == current_user.id,
            ThrottlingEvent.detected_at >= start_date
        )
    ).group_by(func.date(ThrottlingEvent.detected_at))
    
    daily_result = await db.execute(daily_query)
    daily_events = daily_result.all()
    
    return {
        "period_days": days,
        "total_events": total_events,
        "events_by_type": [
            {
                "type": stat.throttling_type,
                "count": stat.count,
                "avg_confidence": float(stat.avg_confidence) if stat.avg_confidence else 0,
                "avg_speed_reduction": float(stat.avg_reduction) if stat.avg_reduction else 0
            }
            for stat in type_stats
        ],
        "daily_events": [
            {"date": str(d.date), "count": d.count}
            for d in daily_events
        ]
    }


@router.get("/quick-check")
async def quick_throttling_check(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Quick check for current throttling status.
    
    Analyzes the most recent measurements.
    """
    # Get last 10 measurements
    query = select(NetworkLog).where(
        NetworkLog.user_id == current_user.id
    ).order_by(NetworkLog.timestamp.desc()).limit(10)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if not logs:
        return {
            "status": "no_data",
            "message": "No network data available for analysis"
        }
    
    # Quick analysis on most recent
    latest = logs[0]
    quick_result = prediction_engine.quick_check(latest.to_dict())
    
    return {
        "status": "throttling" if quick_result.get('is_anomaly') else "normal",
        "latest_measurement": {
            "download_speed": latest.download_speed,
            "upload_speed": latest.upload_speed,
            "ping": latest.ping,
            "timestamp": latest.timestamp.isoformat()
        },
        "analysis": quick_result
    }


@router.get("/predictions")
async def get_throttling_predictions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    hours_ahead: int = Query(6, ge=1, le=24)
):
    """
    Predict future network performance and potential throttling.
    """
    # Get recent data for prediction
    query = select(NetworkLog).where(
        NetworkLog.user_id == current_user.id
    ).order_by(NetworkLog.timestamp.desc()).limit(48)  # Last 48 measurements
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if len(logs) < 24:
        return {
            "error": "Not enough data for predictions",
            "required": 24,
            "available": len(logs)
        }
    
    # Reverse to chronological order
    data = [log.to_dict() for log in reversed(logs)]
    
    # Get predictions
    predictions = prediction_engine.time_series_analyzer.predict_next(data, steps=hours_ahead)
    
    return {
        "predictions": predictions,
        "based_on_samples": len(logs),
        "generated_at": datetime.utcnow().isoformat()
    }


async def store_throttling_events(user_id: int, events: List[Dict], db: AsyncSession):
    """
    Background task to store detected throttling events.
    """
    for event_data in events:
        event = ThrottlingEvent(
            user_id=user_id,
            throttling_detected=True,
            confidence=event_data.get('confidence', 0),
            throttling_type=event_data.get('throttling_type', 'unknown'),
            affected_services=event_data.get('affected_services'),
            start_time=datetime.fromisoformat(event_data['timestamp']) if event_data.get('timestamp') else datetime.utcnow(),
            detection_model="PredictionEngine",
            model_version="1.0"
        )
        db.add(event)
    
    await db.commit()
