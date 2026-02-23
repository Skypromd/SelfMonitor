"""
Configuration management for SelfMonitor Recommendation Engine
"""

from typing import List, Optional, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    APP_NAME: str = "SelfMonitor Recommendation Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    LOG_LEVEL: str = Field(default="INFO")
    
    # Security settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://app.selfmonitor.ai"]
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "*.selfmonitor.ai"]
    )
    SECRET_KEY: str = Field()
    
    # Database settings
    DATABASE_URL: str = Field()
    REDIS_URL: str = Field(default="redis://localhost:6379")
    
    # Vector Database settings
    WEAVIATE_URL: str = Field(default="http://localhost:8080")
    WEAVIATE_API_KEY: Optional[str] = Field(default=None)
    
    # ML Model settings
    MODEL_REGISTRY_PATH: str = Field(default="/app/models")
    MODEL_UPDATE_INTERVAL: int = Field(default=3600)  # seconds
    ENABLE_AUTO_RETRAIN: bool = Field(default=True)
    
    # Real-time processing settings
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092")
    RECOMMENDATION_TOPIC: str = Field(default="user-recommendations")
    USER_EVENTS_TOPIC: str = Field(default="user-events")
    
    # Cache settings
    CACHE_TTL: int = Field(default=300)  # 5 minutes
    RECOMMENDATION_CACHE_TTL: int = Field(default=1800)  # 30 minutes
    
    # A/B Testing settings
    AB_TEST_ENABLED: bool = Field(default=True)
    DEFAULT_AB_SPLIT: float = Field(default=0.5)
    
    # Performance settings
    MAX_RECOMMENDATIONS_PER_REQUEST: int = Field(default=20)
    RECOMMENDATION_TIMEOUT: int = Field(default=2000)  # milliseconds
    BATCH_PROCESSING_SIZE: int = Field(default=1000)
    
    # Monitoring settings
    ENABLE_METRICS: bool = Field(default=True)
    METRICS_PORT: int = Field(default=8001)
    
    # External service URLs
    USER_PROFILE_SERVICE_URL: str = Field(default="http://user-profile-service:8000")
    TRANSACTIONS_SERVICE_URL: str = Field(default="http://transactions-service:8000")
    ANALYTICS_SERVICE_URL: str = Field(default="http://analytics-service:8000")
    AI_AGENT_SERVICE_URL: str = Field(default="http://ai-agent-service:8000")
    
    @field_validator("ALLOWED_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def split_origins_and_hosts(cls, v: Any) -> list[str]:
        """Split comma-separated strings into lists."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: Any) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("DEFAULT_AB_SPLIT")
    @classmethod
    def validate_ab_split(cls, v: Any) -> float:
        """Validate A/B test split ratio."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("DEFAULT_AB_SPLIT must be between 0.0 and 1.0")
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


# Global settings instance
settings = Settings(
    SECRET_KEY="dummy-secret-key-for-development",
    DATABASE_URL="sqlite:///./test.db"
)