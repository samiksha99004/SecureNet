"""
SecureNet Backend — Configuration Management

Loads all environment variables and provides type-safe access
to configuration throughout the application.
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "SecureNet"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # OTP
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 10
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 5
    
    # Email
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "securenet@example.com"
    SMTP_FROM_NAME: str = "SecureNet"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    
    # ML Models
    ML_MODELS_DIR: str = "./models"
    ISOLATION_FOREST_MODEL_PATH: str = "./models/isolation_forest.joblib"
    XGBOOST_MODEL_PATH: str = "./models/xgboost_classifier.joblib"
    FEATURE_SCALER_PATH: str = "./models/feature_scaler.joblib"
    FEATURE_COUNT: int = 78
    
    # ML Thresholds
    ANOMALY_THRESHOLD: float = 0.5
    CLASSIFICATION_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Detection
    DETECTION_ENABLED: bool = True
    DETECTION_MODE: str = "monitor"
    ANALYSIS_INTERVAL_SECONDS: int = 5
    MIN_FLOWS_FOR_ANALYSIS: int = 10
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MESSAGE_QUEUE_SIZE: int = 1000
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/securenet.log"
    
    # Reports
    REPORTS_DIR: str = "./reports"
    MAX_REPORT_SIZE_MB: int = 50
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Security
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
