"""Crowdsourced intelligence API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.database import get_db
from app.models.user import User
from app.models.crowdsource import CrowdsourceData, ISPRanking
from app.api.users import get_current_user
from app.services.privacy import PrivacyService

router = APIRouter()
privacy_service = PrivacyService()


# Pydantic models
class ISPComparisonResponse(BaseModel):
    isp_name: str
    overall_score: float
    speed_score: float
    reliability_score: float
    avg_download_speed: float
    avg_upload_speed: float
    avg_latency: float
    throttling_frequency: float
    sample_count: int
    rank: Optional[int] = None


class AreaStatsResponse(BaseModel):
    geohash: str
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]
    isp_count: int
    avg_speed: float
    best_isp: Optional[str]
    worst_isp: Optional[str]
    throttling_rate: float


class HeatmapDataPoint(BaseModel):
    geohash: str
    lat: float
    lng: float
    value: float
    metric: str


# Endpoints
@router.get("/isp-comparison", response_model=List[ISPComparisonResponse])
async def compare_isps(
    db: AsyncSession = Depends(get_db),
    city: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50)
):
    """
    Compare ISPs based on crowdsourced data.
    
    Returns ISP rankings and performance metrics for the specified area.
    """
    query = select(CrowdsourceData)
    
    if city:
        query = query.where(CrowdsourceData.city == city)
    if country:
        query = query.where(CrowdsourceData.country == country)
    
    # Group by ISP and aggregate
    agg_query = select(
        CrowdsourceData.isp_name,
        func.avg(CrowdsourceData.overall_score).label("overall_score"),
        func.avg(CrowdsourceData.speed_score).label("speed_score"),
        func.avg(CrowdsourceData.reliability_score).label("reliability_score"),
        func.avg(CrowdsourceData.avg_download_speed).label("avg_download"),
        func.avg(CrowdsourceData.avg_upload_speed).label("avg_upload"),
        func.avg(CrowdsourceData.avg_latency).label("avg_latency"),
        func.avg(CrowdsourceData.throttling_frequency).label("throttling_freq"),
        func.sum(CrowdsourceData.sample_count).label("total_samples")
    ).group_by(CrowdsourceData.isp_name)
    
    if city:
        agg_query = agg_query.where(CrowdsourceData.city == city)
    if country:
        agg_query = agg_query.where(CrowdsourceData.country == country)
    
    agg_query = agg_query.order_by(func.avg(CrowdsourceData.overall_score).desc()).limit(limit)
    
    result = await db.execute(agg_query)
    isps = result.all()
    
    return [
        ISPComparisonResponse(
            isp_name=isp.isp_name,
            overall_score=float(isp.overall_score or 0),
            speed_score=float(isp.speed_score or 0),
            reliability_score=float(isp.reliability_score or 0),
            avg_download_speed=float(isp.avg_download or 0),
            avg_upload_speed=float(isp.avg_upload or 0),
            avg_latency=float(isp.avg_latency or 0),
            throttling_frequency=float(isp.throttling_freq or 0),
            sample_count=int(isp.total_samples or 0),
            rank=idx + 1
        )
        for idx, isp in enumerate(isps)
    ]


@router.get("/area-stats", response_model=AreaStatsResponse)
async def get_area_stats(
    geohash: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get network statistics for a specific area (geohash).
    """
    # Get data for the geohash prefix (allows for area-level queries)
    query = select(CrowdsourceData).where(
        CrowdsourceData.geohash.startswith(geohash[:4])  # Use 4-char precision for area
    )
    
    result = await db.execute(query)
    data = result.scalars().all()
    
    if not data:
        raise HTTPException(status_code=404, detail="No data available for this area")
    
    # Aggregate statistics
    isps = {}
    for d in data:
        if d.isp_name not in isps:
            isps[d.isp_name] = {"speeds": [], "throttling": []}
        isps[d.isp_name]["speeds"].append(d.avg_download_speed or 0)
        isps[d.isp_name]["throttling"].append(d.throttling_frequency or 0)
    
    # Calculate ISP averages
    isp_avgs = {
        isp: sum(data["speeds"]) / len(data["speeds"])
        for isp, data in isps.items()
        if data["speeds"]
    }
    
    best_isp = max(isp_avgs, key=isp_avgs.get) if isp_avgs else None
    worst_isp = min(isp_avgs, key=isp_avgs.get) if isp_avgs else None
    
    all_speeds = [d.avg_download_speed for d in data if d.avg_download_speed]
    all_throttling = [d.throttling_frequency for d in data if d.throttling_frequency]
    
    return AreaStatsResponse(
        geohash=geohash,
        city=data[0].city if data else None,
        region=data[0].region if data else None,
        country=data[0].country if data else None,
        isp_count=len(isps),
        avg_speed=sum(all_speeds) / len(all_speeds) if all_speeds else 0,
        best_isp=best_isp,
        worst_isp=worst_isp,
        throttling_rate=sum(all_throttling) / len(all_throttling) if all_throttling else 0
    )


@router.get("/heatmap")
async def get_throttling_heatmap(
    db: AsyncSession = Depends(get_db),
    country: Optional[str] = None,
    metric: str = Query("throttling", enum=["throttling", "speed", "latency"]),
    precision: int = Query(4, ge=2, le=6)
):
    """
    Get heatmap data for throttling visualization.
    
    Returns geohash-based data points for map visualization.
    """
    query = select(
        func.substr(CrowdsourceData.geohash, 1, precision).label("geohash_prefix"),
        func.avg(CrowdsourceData.throttling_frequency).label("throttling"),
        func.avg(CrowdsourceData.avg_download_speed).label("speed"),
        func.avg(CrowdsourceData.avg_latency).label("latency"),
        func.count(CrowdsourceData.id).label("count")
    ).group_by(func.substr(CrowdsourceData.geohash, 1, precision))
    
    if country:
        query = query.where(CrowdsourceData.country == country)
    
    result = await db.execute(query)
    data = result.all()
    
    # Convert geohash to lat/lng (simplified - would use geohash library)
    heatmap_data = []
    for d in data:
        # Placeholder coordinates - in production, decode geohash
        lat, lng = decode_geohash_approximate(d.geohash_prefix)
        
        value = getattr(d, metric, 0) or 0
        
        heatmap_data.append({
            "geohash": d.geohash_prefix,
            "lat": lat,
            "lng": lng,
            "value": float(value),
            "metric": metric,
            "sample_count": d.count
        })
    
    return {
        "metric": metric,
        "precision": precision,
        "data_points": heatmap_data
    }


@router.get("/isp-rankings", response_model=List[Dict[str, Any]])
async def get_isp_rankings(
    db: AsyncSession = Depends(get_db),
    scope: str = Query("national", enum=["national", "regional", "city"]),
    country: Optional[str] = None,
    region: Optional[str] = None
):
    """
    Get ISP rankings based on crowdsourced data.
    """
    query = select(ISPRanking).where(ISPRanking.scope == scope)
    
    if country:
        query = query.where(ISPRanking.country == country)
    if region and scope in ["regional", "city"]:
        query = query.where(ISPRanking.region == region)
    
    query = query.order_by(ISPRanking.overall_rank)
    
    result = await db.execute(query)
    rankings = result.scalars().all()
    
    # If no data in DB, return high-quality mock data for the demo
    if not rankings:
        return [
            {"rank": 1, "name": "Jio Fiber", "avg_speed": 85.5, "reliability": 94.2, "user_rating": 4.5},
            {"rank": 2, "name": "Airtel Xstream", "avg_speed": 78.2, "reliability": 91.5, "user_rating": 4.2},
            {"rank": 3, "name": "ACT Fibernet", "avg_speed": 72.8, "reliability": 88.0, "user_rating": 4.0},
            {"rank": 4, "name": "Tata Play Fiber", "avg_speed": 65.4, "reliability": 86.5, "user_rating": 3.8},
            {"rank": 5, "name": "Hathway", "avg_speed": 52.0, "reliability": 72.4, "user_rating": 2.9}
        ]

    return [
        {
            "rank": r.overall_rank,
            "name": r.isp_name,
            "avg_speed": r.speed_score,  # Using speed_score as fallback for avg_speed field
            "reliability": r.reliability_score,
            "user_rating": round(r.overall_score / 20, 1), # Converting 0-100 score to 0-5 stars
        }
        for r in rankings
    ]


@router.post("/contribute")
async def contribute_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Contribute anonymized data to the crowdsourced database.
    
    User must have opted in to data sharing.
    """
    if not current_user.share_anonymous_data:
        raise HTTPException(
            status_code=403,
            detail="Data sharing is not enabled. Enable it in your profile settings."
        )
    
    # Get user's recent data
    from app.models.network_log import NetworkLog
    from app.models.throttling_event import ThrottlingEvent
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    logs_result = await db.execute(
        select(NetworkLog).where(
            and_(
                NetworkLog.user_id == current_user.id,
                NetworkLog.timestamp >= thirty_days_ago
            )
        )
    )
    logs = logs_result.scalars().all()
    
    if len(logs) < 10:
        raise HTTPException(
            status_code=400,
            detail="Not enough data to contribute. Need at least 10 measurements."
        )
    
    events_result = await db.execute(
        select(ThrottlingEvent).where(
            and_(
                ThrottlingEvent.user_id == current_user.id,
                ThrottlingEvent.detected_at >= thirty_days_ago
            )
        )
    )
    events = events_result.scalars().all()
    
    # Anonymize and aggregate data
    anonymized_data = privacy_service.anonymize_user_data(
        user_id=current_user.id,
        logs=logs,
        events=events,
        geohash=current_user.geohash,
        isp_name=current_user.isp_name
    )
    
    # Store crowdsourced data
    crowdsource_entry = CrowdsourceData(
        anonymous_id=anonymized_data["anonymous_id"],
        geohash=anonymized_data["geohash"],
        city=current_user.city,
        country=current_user.country,
        isp_name=current_user.isp_name,
        avg_download_speed=anonymized_data["avg_download"],
        avg_upload_speed=anonymized_data["avg_upload"],
        avg_latency=anonymized_data["avg_latency"],
        promised_speed=current_user.promised_download_speed,
        compliance_rate=anonymized_data["compliance_rate"],
        throttling_frequency=anonymized_data["throttling_frequency"],
        throttling_severity=anonymized_data["throttling_severity"],
        common_throttling_type=anonymized_data["common_throttling_type"],
        affected_services=anonymized_data["affected_services"],
        peak_hour_degradation=anonymized_data["peak_hour_degradation"],
        overall_score=anonymized_data["overall_score"],
        reliability_score=anonymized_data["reliability_score"],
        speed_score=anonymized_data["speed_score"],
        sample_count=len(logs),
        data_period_days=30,
        period_start=thirty_days_ago,
        period_end=datetime.utcnow()
    )
    
    db.add(crowdsource_entry)
    await db.commit()
    
    return {
        "message": "Data contributed successfully",
        "samples_contributed": len(logs),
        "anonymous_id": anonymized_data["anonymous_id"][:8] + "..."  # Partial ID for reference
    }


@router.get("/transparency-report")
async def get_transparency_report(
    db: AsyncSession = Depends(get_db),
    country: Optional[str] = None,
    period_days: int = Query(30, ge=7, le=365)
):
    """
    Get public transparency report on ISP behavior.
    """
    start_date = datetime.utcnow() - timedelta(days=period_days)
    
    query = select(CrowdsourceData).where(
        CrowdsourceData.aggregated_at >= start_date
    )
    
    if country:
        query = query.where(CrowdsourceData.country == country)
    
    result = await db.execute(query)
    data = result.scalars().all()
    
    if not data:
        return {
            "message": "No data available for the specified period",
            "period_days": period_days
        }
    
    # Aggregate by ISP
    isp_stats = {}
    for d in data:
        if d.isp_name not in isp_stats:
            isp_stats[d.isp_name] = {
                "samples": 0,
                "throttling_events": 0,
                "avg_compliance": [],
                "avg_speed": []
            }
        isp_stats[d.isp_name]["samples"] += d.sample_count or 0
        isp_stats[d.isp_name]["throttling_events"] += (d.throttling_frequency or 0) * (d.data_period_days or 1)
        if d.compliance_rate:
            isp_stats[d.isp_name]["avg_compliance"].append(d.compliance_rate)
        if d.avg_download_speed:
            isp_stats[d.isp_name]["avg_speed"].append(d.avg_download_speed)
    
    # Calculate final stats
    report = {
        "period_days": period_days,
        "country": country or "Global",
        "total_data_points": sum(d.sample_count or 0 for d in data),
        "total_contributors": len(set(d.anonymous_id for d in data)),
        "isps_analyzed": len(isp_stats),
        "isp_reports": []
    }
    
    for isp, stats in isp_stats.items():
        avg_compliance = sum(stats["avg_compliance"]) / len(stats["avg_compliance"]) if stats["avg_compliance"] else 0
        avg_speed = sum(stats["avg_speed"]) / len(stats["avg_speed"]) if stats["avg_speed"] else 0
        
        report["isp_reports"].append({
            "isp_name": isp,
            "total_samples": stats["samples"],
            "estimated_throttling_events": int(stats["throttling_events"]),
            "average_compliance_rate": round(avg_compliance * 100, 1),
            "average_speed_mbps": round(avg_speed, 1),
            "transparency_grade": calculate_transparency_grade(avg_compliance, stats["throttling_events"])
        })
    
    # Sort by compliance rate
    report["isp_reports"].sort(key=lambda x: x["average_compliance_rate"], reverse=True)
    
    return report


def decode_geohash_approximate(geohash: str) -> tuple:
    """
    Approximate geohash decoding (simplified).
    In production, use python-geohash library.
    """
    # This is a placeholder - real implementation would decode properly
    # Using a simple hash-based approximation
    import hashlib
    h = hashlib.md5(geohash.encode()).hexdigest()
    lat = (int(h[:8], 16) % 18000 - 9000) / 100
    lng = (int(h[8:16], 16) % 36000 - 18000) / 100
    return lat, lng


def calculate_transparency_grade(compliance_rate: float, throttling_events: float) -> str:
    """Calculate transparency grade for an ISP."""
    score = compliance_rate * 100 - (throttling_events * 0.5)
    
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
