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
from app.models.database import init_db


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO"
)
logger.add("logs/nettruth.log", rotation="10 MB", retention="7 days")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting NetTruth Platform...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
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
