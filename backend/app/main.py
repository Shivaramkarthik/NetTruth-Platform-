"""NetTruth - AI-Powered ISP Throttling Detection Platform

Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import settings
from app.api import network, throttling, reports, crowdsource, users, dashboard
from app.services.scheduler import start_scheduler, stop_scheduler
from app.models.database import init_db, async_session
from sqlalchemy import select, func


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO"
)
logger.add("logs/nettruth.log", rotation="10 MB", retention="7 days")


async def seed_demo_data():
    """Seed database with demo data if tables are empty."""
    from app.models.crowdsource import ISPRanking
    from app.models.network_log import NetworkLog
    from app.models.user import User
    from datetime import datetime, timedelta

    async with async_session() as db:
        # Check if ISP rankings exist
        result = await db.execute(select(func.count(ISPRanking.id)))
        count = result.scalar()

        if count == 0:
            logger.info("Seeding ISP rankings with demo data...")
            rankings = [
                ISPRanking(isp_name="Jio Fiber", scope="national", country="India",
                           overall_rank=1, speed_rank=1, reliability_rank=2, value_rank=1,
                           overall_score=88.5, speed_score=92.0, reliability_score=85.0, transparency_score=80.0,
                           total_users=15200, total_measurements=456000, avg_throttling_rate=0.05, percentile=95.0),
                ISPRanking(isp_name="Airtel Xstream", scope="national", country="India",
                           overall_rank=2, speed_rank=2, reliability_rank=1, value_rank=3,
                           overall_score=86.2, speed_score=88.0, reliability_score=90.0, transparency_score=82.0,
                           total_users=12800, total_measurements=384000, avg_throttling_rate=0.07, percentile=90.0),
                ISPRanking(isp_name="ACT Fibernet", scope="national", country="India",
                           overall_rank=3, speed_rank=3, reliability_rank=3, value_rank=2,
                           overall_score=82.0, speed_score=85.0, reliability_score=80.0, transparency_score=78.0,
                           total_users=8500, total_measurements=255000, avg_throttling_rate=0.08, percentile=82.0),
                ISPRanking(isp_name="Vi (Vodafone Idea)", scope="national", country="India",
                           overall_rank=4, speed_rank=5, reliability_rank=4, value_rank=4,
                           overall_score=72.5, speed_score=70.0, reliability_score=74.0, transparency_score=68.0,
                           total_users=9200, total_measurements=276000, avg_throttling_rate=0.12, percentile=65.0),
                ISPRanking(isp_name="BSNL", scope="national", country="India",
                           overall_rank=5, speed_rank=6, reliability_rank=5, value_rank=5,
                           overall_score=62.0, speed_score=58.0, reliability_score=65.0, transparency_score=60.0,
                           total_users=11000, total_measurements=330000, avg_throttling_rate=0.18, percentile=45.0),
                ISPRanking(isp_name="Hathway", scope="national", country="India",
                           overall_rank=6, speed_rank=4, reliability_rank=6, value_rank=6,
                           overall_score=68.0, speed_score=75.0, reliability_score=62.0, transparency_score=55.0,
                           total_users=4200, total_measurements=126000, avg_throttling_rate=0.15, percentile=55.0),
            ]
            for r in rankings:
                db.add(r)
            await db.commit()
            logger.info(f"Seeded {len(rankings)} ISP rankings")

        # Ensure demo user has at least one network log for dashboard
        result = await db.execute(select(User).where(User.email == "demo@nettruth.ai"))
        demo_user = result.scalar_one_or_none()

        if demo_user:
            log_result = await db.execute(select(func.count(NetworkLog.id)).where(NetworkLog.user_id == demo_user.id))
            log_count = log_result.scalar()

            if log_count == 0:
                import random
                logger.info("Seeding network logs for demo user...")
                now = datetime.utcnow()
                for i in range(10):
                    log = NetworkLog(
                        user_id=demo_user.id,
                        download_speed=round(random.uniform(60, 95), 2),
                        upload_speed=round(random.uniform(25, 50), 2),
                        ping=round(random.uniform(10, 30), 2),
                        jitter=round(random.uniform(1, 5), 2),
                        packet_loss=round(random.uniform(0, 0.5), 2),
                        isp_name=demo_user.isp_name,
                        promised_download=demo_user.promised_download_speed,
                        promised_upload=demo_user.promised_upload_speed,
                        test_type="automatic",
                        target_service="general",
                        timestamp=now - timedelta(hours=i * 2)
                    )
                    db.add(log)
                await db.commit()
                logger.info("Seeded 10 network log entries for demo user")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting NetTruth Platform...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Seed demo data if tables are empty
    await seed_demo_data()

    # Start background scheduler for network monitoring
    start_scheduler()
    logger.info("Background scheduler started")

    yield

    # Cleanup
    stop_scheduler()
    logger.info("NetTruth Platform shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="NetTruth API",
    description="""
    ## AI-Powered ISP Throttling Detection Platform

    NetTruth provides:
    - 📡 Real-time network monitoring
    - 🤖 AI-based throttling detection
    - 📊 Smart dashboard with insights
    - 📄 Legal report generation
    - 🌍 Crowdsourced ISP intelligence
    - 🔐 Privacy-first data handling
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(network.router, prefix="/api/v1/network", tags=["Network Monitoring"])
app.include_router(throttling.router, prefix="/api/v1/throttling", tags=["Throttling Detection"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Legal Reports"])
app.include_router(crowdsource.router, prefix="/api/v1/crowdsource", tags=["Crowdsourced Data"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "message": "Welcome to NetTruth - AI-Powered ISP Throttling Detection Platform"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "api": "operational",
            "database": "operational",
            "ml_engine": "operational",
            "scheduler": "operational"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
