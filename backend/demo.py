"""NetTruth Demo API - Simplified version for demonstration."""
from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timedelta
# Import removed for standalone demo
import random
import uvicorn
import uuid

app = FastAPI(
    title="NetTruth API",
    description="AI-Powered ISP Throttling Detection Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Settings
SECRET_KEY = "nettruth-demo-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing removed for demo
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

# In-memory user storage (for demo purposes)
users_db: Dict[str, dict] = {}

# User Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    isp_name: Optional[str] = None
    promised_download_speed: Optional[float] = None
    promised_upload_speed: Optional[float] = None
    plan_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    uuid: str
    email: str
    full_name: Optional[str] = None
    isp_name: Optional[str] = None
    promised_download_speed: Optional[float] = None
    promised_upload_speed: Optional[float] = None
    plan_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    share_anonymous_data: bool = True
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    return password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return "dummy-access-token"

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    if not users_db:
        # Fallback dummy user if none registered
        return {
            "id": 1,
            "uuid": str(uuid.uuid4()),
            "email": "test@nettruth.com",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": True,
            "share_anonymous_data": True,
            "created_at": datetime.utcnow()
        }
    # Return first user for demo simplicity without jose token decoding
    return list(users_db.values())[0]

# User Endpoints
@app.post("/api/v1/users/register", response_model=UserResponse, status_code=201)
async def register_user(user_data: UserCreate):
    """Register a new user."""
    if user_data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = len(users_db) + 1
    user = {
        "id": user_id,
        "uuid": str(uuid.uuid4()),
        "email": user_data.email,
        "hashed_password": get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "isp_name": user_data.isp_name,
        "promised_download_speed": user_data.promised_download_speed,
        "promised_upload_speed": user_data.promised_upload_speed,
        "plan_name": user_data.plan_name,
        "city": user_data.city,
        "country": user_data.country,
        "is_active": True,
        "is_verified": False,
        "share_anonymous_data": True,
        "created_at": datetime.utcnow()
    }
    users_db[user_data.email] = user
    return UserResponse(**{k: v for k, v in user.items() if k != "hashed_password"})

@app.post("/api/v1/users/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token."""
    user = users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(
        data={"sub": user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(**{k: v for k, v in current_user.items() if k != "hashed_password"})

# Models
class SpeedTestResult(BaseModel):
    download_speed: float
    upload_speed: float
    latency: float
    timestamp: str
    server: str = "Mumbai, India"

class ThrottlingAnalysis(BaseModel):
    throttling_detected: bool
    confidence: float
    type: str
    affected_services: List[str]
    severity: str
    recommendation: str

class ISPRanking(BaseModel):
    rank: int
    name: str
    avg_speed: float
    reliability: float
    user_rating: float

class DashboardSummary(BaseModel):
    current_speed: dict
    promised_speed: float
    speed_delivery_rate: float
    throttling_status: dict
    alerts: List[dict]

# Demo data
ISP_RANKINGS = [
    ISPRanking(rank=1, name="Jio Fiber", avg_speed=85, reliability=92, user_rating=4.2),
    ISPRanking(rank=2, name="Airtel Xstream", avg_speed=78, reliability=88, user_rating=3.9),
    ISPRanking(rank=3, name="ACT Fibernet", avg_speed=72, reliability=85, user_rating=3.7),
    ISPRanking(rank=4, name="BSNL Fiber", avg_speed=58, reliability=72, user_rating=2.8),
    ISPRanking(rank=5, name="Hathway", avg_speed=52, reliability=68, user_rating=2.5),
]

# Routes
@app.get("/")
async def root():
    return {
        "message": "Welcome to NetTruth API",
        "version": "1.0.0",
        "description": "AI-Powered ISP Throttling Detection Platform",
        "endpoints": {
            "speed_test": "/api/v1/network/speed-test",
            "throttling_analysis": "/api/v1/throttling/analyze",
            "dashboard": "/api/v1/dashboard/summary",
            "isp_rankings": "/api/v1/crowdsource/isp-rankings",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/network/speed-test", response_model=SpeedTestResult)
async def run_speed_test():
    """Run a network speed test."""
    # Simulate speed test results
    return SpeedTestResult(
        download_speed=round(random.uniform(50, 95), 2),
        upload_speed=round(random.uniform(20, 45), 2),
        latency=round(random.uniform(8, 25), 1),
        timestamp=datetime.utcnow().isoformat(),
        server="Mumbai, India"
    )

@app.post("/api/v1/throttling/analyze", response_model=ThrottlingAnalysis)
async def analyze_throttling():
    """Analyze network for throttling using AI models."""
    # Simulate AI analysis
    throttling_detected = random.random() > 0.5
    
    if throttling_detected:
        return ThrottlingAnalysis(
            throttling_detected=True,
            confidence=round(random.uniform(0.75, 0.98), 2),
            type=random.choice(["app-specific", "peak-hour", "data-cap"]),
            affected_services=random.sample(["YouTube", "Netflix", "Amazon Prime", "Hotstar"], k=random.randint(1, 3)),
            severity=random.choice(["low", "medium", "high"]),
            recommendation="Consider filing a complaint with TRAI"
        )
    else:
        return ThrottlingAnalysis(
            throttling_detected=False,
            confidence=round(random.uniform(0.85, 0.99), 2),
            type="none",
            affected_services=[],
            severity="none",
            recommendation="Your connection appears normal"
        )

@app.get("/api/v1/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary():
    """Get dashboard summary with current network status."""
    download = round(random.uniform(60, 90), 1)
    promised = 100
    
    return DashboardSummary(
        current_speed={
            "download": download,
            "upload": round(random.uniform(30, 45), 1),
            "latency": round(random.uniform(10, 20), 1)
        },
        promised_speed=promised,
        speed_delivery_rate=round(download / promised, 2),
        throttling_status={
            "active": False,
            "last_detected": "2026-03-22T19:30:00Z"
        },
        alerts=[
            {
                "id": "1",
                "type": "info",
                "severity": "info",
                "message": "Speed monitoring active",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    )

@app.get("/api/v1/dashboard/speed-trends")
async def get_speed_trends(hours: int = 24):
    trends = []
    now = datetime.utcnow()
    for i in range(hours):
        t = now - timedelta(hours=hours-i)
        trends.append({
            "timestamp": t.isoformat(),
            "download_speed": round(random.uniform(60, 95), 1),
            "upload_speed": round(random.uniform(20, 40), 1)
        })
    return trends

@app.get("/api/v1/dashboard/isp-rating")
async def get_isp_rating():
    return {
        "overall_score": 85,
        "speed_score": 88,
        "reliability_score": 82,
        "value_score": 75,
        "comparison_to_area": "above_average"
    }

@app.get("/api/v1/throttling/quick-check")
async def get_quick_check():
    return {
        "status": "clear",
        "analysis": {"explanation": "No throttling detected."}
    }

@app.get("/api/v1/network/logs")
async def get_network_logs(limit: int = 10):
    logs = []
    now = datetime.utcnow()
    for i in range(limit):
        t = now - timedelta(days=i)
        logs.append({
            "id": i,
            "timestamp": t.isoformat(),
            "download_speed": round(random.uniform(50, 95), 1),
            "upload_speed": round(random.uniform(20, 45), 1),
            "ping": round(random.uniform(10, 30), 1),
            "download_ratio": round(random.uniform(0.7, 1.0), 2)
        })
    return logs

@app.post("/api/v1/network/speedtest", response_model=SpeedTestResult)
async def run_speed_test_alt():
    """Run a network speed test."""
    return SpeedTestResult(
        download_speed=round(random.uniform(50, 95), 2),
        upload_speed=round(random.uniform(20, 45), 2),
        latency=round(random.uniform(8, 25), 1),
        timestamp=datetime.utcnow().isoformat(),
        server="Mumbai, India"
    )

@app.get("/api/v1/crowdsource/isp-rankings", response_model=List[ISPRanking])
async def get_isp_rankings():
    """Get ISP rankings based on crowdsourced data."""
    return ISP_RANKINGS

@app.get("/api/v1/throttling/predict")
async def predict_throttling():
    """Predict future throttling using ML models."""
    predictions = []
    for hour in range(24):
        predictions.append({
            "hour": f"2026-03-24T{hour:02d}:00:00Z",
            "throttling_probability": round(random.uniform(0.1, 0.9), 2),
            "expected_speed_drop": round(random.uniform(10, 50), 1) if hour >= 19 and hour <= 23 else round(random.uniform(0, 20), 1),
            "likely_type": "peak-hour" if hour >= 19 and hour <= 23 else "normal"
        })
    return {"predictions": predictions}

@app.post("/api/v1/reports/generate")
async def generate_report(report_type: str = "legal"):
    """Generate a legal evidence report."""
    return {
        "id": "report-" + str(random.randint(1000, 9999)),
        "title": f"Legal Evidence Report - {datetime.now().strftime('%B %Y')}",
        "type": report_type,
        "status": "generated",
        "created_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_tests": random.randint(100, 500),
            "throttling_events": random.randint(5, 25),
            "avg_speed_delivery": round(random.uniform(65, 85), 1),
            "compliance_score": round(random.uniform(0.5, 0.8), 2)
        },
        "download_url": "/reports/download/sample.pdf"
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  NetTruth API - AI-Powered ISP Throttling Detection")
    print("="*60)
    print("\n  Starting server at http://localhost:8000")
    print("  API Documentation: http://localhost:8000/docs")
    print("  Health Check: http://localhost:8000/health")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
