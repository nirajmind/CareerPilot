"""
Enhanced configuration management using Pydantic.
Replaces scattered os.getenv() calls with a centralized, typed config class.
Follows SOLID principle: Single Responsibility.
"""

from pydantic import BaseModel, Field, ConfigDict
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)


class SecuritySettings(BaseModel):
    """Security configuration."""
    model_config = ConfigDict(frozen=False)
    
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    # Account Lockout Settings
    max_failed_attempts: int = Field(default=5)
    lockout_duration_hours: int = Field(default=24)
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=10)
    rate_limit_window_minutes: int = Field(default=1)


class DatabaseSettings(BaseModel):
    """Database configuration."""
    model_config = ConfigDict(frozen=False)
    
    mongo_uri: str = Field(default="mongodb://mongo:27017/careerpilot")
    mongo_db_name: str = Field(default="careerpilot")
    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    redis_decode_responses: bool = Field(default=True)


class EmailSettings(BaseModel):
    """Email (Gmail SMTP) configuration."""
    model_config = ConfigDict(frozen=False)
    
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    sender_email: str = Field(..., alias="GMAIL_SENDER_EMAIL")
    sender_password: str = Field(..., alias="GMAIL_APP_PASSWORD")  # Gmail app-specific password
    
    # Password reset token expiry in hours
    password_reset_token_expiry_hours: int = Field(default=24)


class StripeSettings(BaseModel):
    """Stripe payment configuration."""
    model_config = ConfigDict(frozen=False)
    
    stripe_api_key: str = Field(..., alias="STRIPE_API_KEY")
    stripe_webhook_secret: str = Field(..., alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id_premium: str = Field(..., alias="STRIPE_PRICE_ID_PREMIUM")


class QuotaSettings(BaseModel):
    """Usage quota configuration."""
    model_config = ConfigDict(frozen=False)
    
    free_tier_daily_limit: int = Field(default=5)  # 5 analyses per day
    premium_tier_daily_limit: int = Field(default=100)  # 100 analyses per day


class APISettings(BaseModel):
    """API configuration."""
    model_config = ConfigDict(frozen=False)
    
    api_title: str = Field(default="CareerPilot API")
    api_version: str = Field(default="0.1.0")
    log_level: str = Field(default="INFO")


class GeminiSettings(BaseModel):
    """Gemini API configuration."""
    model_config = ConfigDict(frozen=False)
    
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_proxy_url: str = Field(..., alias="GEMINI_PROXY_URL")
    gemini_proxy_secret: str = Field(..., alias="PROXY_SECRET")
    gemini_model: str = Field(default="models/gemini-pro")
    gemini_vision_model: str = Field(default="models/gemini-pro-vision")
    gemini_embedding_model: str = Field(default="v1/models/text-embedding-004")
    
    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = Field(default=5)
    circuit_breaker_recovery_timeout_seconds: int = Field(default=60)


class TracingSettings(BaseModel):
    """OpenTelemetry tracing configuration."""
    model_config = ConfigDict(frozen=False)

    enabled: bool = Field(default=True)
    service_name: str = Field(default="careerpilot-api")
    otlp_endpoint: str = Field(default="http://localhost:4317")  # Standard gRPC port


class AppConfig(BaseModel):
    """Root configuration aggregating all settings."""
    model_config = ConfigDict(frozen=False)
    
    security: SecuritySettings
    database: DatabaseSettings
    email: EmailSettings
    stripe: StripeSettings
    quota: QuotaSettings
    api: APISettings
    gemini: GeminiSettings
    tracing: TracingSettings


def load_config() -> AppConfig:
    """
    Load and validate configuration from environment variables.
    Raises ValidationError if required vars are missing.
    """
    return AppConfig(
        security=SecuritySettings(
            jwt_secret_key=os.getenv("JWT_SECRET_KEY"),
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            max_failed_attempts=int(os.getenv("MAX_FAILED_ATTEMPTS", "5")),
            lockout_duration_hours=int(os.getenv("LOCKOUT_DURATION_HOURS", "24")),
        ),
        database=DatabaseSettings(
            mongo_uri=os.getenv("MONGO_URI", "mongodb://mongo:27017/careerpilot"),
            redis_host=os.getenv("REDIS_HOST", "redis"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
        ),
        email=EmailSettings(
            sender_email=os.getenv("GMAIL_SENDER_EMAIL"),
            sender_password=os.getenv("GMAIL_APP_PASSWORD"),
            password_reset_token_expiry_hours=int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRY_HOURS", "24")),
        ),
        stripe=StripeSettings(
            stripe_api_key=os.getenv("STRIPE_API_KEY"),
            stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
            stripe_price_id_premium=os.getenv("STRIPE_PRICE_ID_PREMIUM"),
        ),
        quota=QuotaSettings(
            free_tier_daily_limit=int(os.getenv("FREE_TIER_DAILY_LIMIT", "5")),
            premium_tier_daily_limit=int(os.getenv("PREMIUM_TIER_DAILY_LIMIT", "100")),
        ),
        api=APISettings(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        ),
        gemini=GeminiSettings(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_proxy_url=os.getenv("GEMINI_PROXY_URL"),
            gemini_proxy_secret=os.getenv("PROXY_SECRET"),
            gemini_model=os.getenv("GEMINI_MODEL", "models/gemini-pro"),
            gemini_vision_model=os.getenv("GEMINI_VISION_MODEL", "models/gemini-pro-vision"),
        ),
        tracing=TracingSettings(
            enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
            service_name=os.getenv("TRACING_SERVICE_NAME", "careerpilot-api"),
            otlp_endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4317"),
        ),
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """
    Cached config loader.
    Uses @lru_cache to load config only once per application lifetime.
    """
    return load_config()
