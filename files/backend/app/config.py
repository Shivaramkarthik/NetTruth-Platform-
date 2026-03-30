from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "NetTruth"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./nettruth.db"

    @validator("DATABASE_URL", pre=False, always=True)
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    # InfluxDB (Time-series)
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = "your-influxdb-token"
    INFLUXDB_ORG: str = "nettruth"
    INFLUXDB_BUCKET: str = "network_metrics"
    
    # ML Model Paths
    ML_MODEL_PATH: str = "./ml_models"
    
    # Privacy Settings
    ANONYMIZATION_SALT: str = "nettruth-anonymization-salt"
    DIFFERENTIAL_PRIVACY_EPSILON: float = 1.0
    
    # Network Testing
    SPEED_TEST_INTERVAL: int = 300  # seconds (5 minutes)
    PING_INTERVAL: int = 60  # seconds
    
    # JWT Settings
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
