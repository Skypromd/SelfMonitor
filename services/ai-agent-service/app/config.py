"""
Configuration for SelfMate AI Agent Service

Comprehensive configuration management for all components.
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration"""
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    weaviate_url: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    weaviate_api_key: str = os.getenv("WEAVIATE_API_KEY", "")
    
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_user: str = os.getenv("POSTGRES_USER", "selfmonitor")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    postgres_db: str = os.getenv("POSTGRES_DB", "selfmonitor")


@dataclass
class AIConfig:
    """AI model configuration"""
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-0125-preview")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "2000"))
    
    # Personality settings
    agent_name: str = "SelfMate"
    personality_type: str = "professional_friendly"
    expertise_level: str = "expert"
    
    # Conversation settings
    context_window: int = 10  # Number of previous messages to include
    max_conversation_length: int = 100  # Max turns per conversation


@dataclass
class ServiceConfig:
    """Service discovery and integration"""
    service_registry_url: str = os.getenv("SERVICE_REGISTRY_URL", "http://localhost:8080")
    
    # Microservice endpoints
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
    user_profile_service_url: str = os.getenv("USER_PROFILE_SERVICE_URL", "http://localhost:8002")
    transactions_service_url: str = os.getenv("TRANSACTIONS_SERVICE_URL", "http://localhost:8003")
    analytics_service_url: str = os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:8004")
    categorization_service_url: str = os.getenv("CATEGORIZATION_SERVICE_URL", "http://localhost:8005")
    banking_connector_url: str = os.getenv("BANKING_CONNECTOR_URL", "http://localhost:8006")
    tax_engine_url: str = os.getenv("TAX_ENGINE_URL", "http://localhost:8007")
    compliance_service_url: str = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8008")
    advice_service_url: str = os.getenv("ADVICE_SERVICE_URL", "http://localhost:8009")
    
    # Service authentication
    service_api_key: str = os.getenv("SERVICE_API_KEY", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "your-secret-key")


@dataclass
class MemoryConfig:
    """Memory system configuration"""
    # Redis memory settings
    session_ttl: int = int(os.getenv("SESSION_TTL", "7200"))  # 2 hours
    conversation_ttl: int = int(os.getenv("CONVERSATION_TTL", "86400"))  # 24 hours
    user_profile_ttl: int = int(os.getenv("USER_PROFILE_TTL", "604800"))  # 1 week
    
    # Weaviate memory settings
    memory_index_name: str = "SelfMateMemory"
    conversation_index_name: str = "SelfMateConversations"
    max_memory_entries: int = 10000
    similarity_threshold: float = 0.8
    
    # Memory optimization
    cleanup_interval: int = 3600  # 1 hour
    compression_enabled: bool = True


@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100  # requests per minute per user
    
    enable_request_logging: bool = True
    log_sensitive_data: bool = False
    
    cors_origins: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:3000", "https://selfmonitor.app"]


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    enable_metrics: bool = True
    enable_health_checks: bool = True
    
    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    grafana_url: str = os.getenv("GRAFANA_URL", "http://localhost:3000")
    
    # Logging configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = "json"
    
    # Performance monitoring
    response_time_threshold: float = 2.0  # seconds
    memory_usage_threshold: float = 0.8  # 80%


class Config:
    """Main configuration class"""
    
    def __init__(self):
        # Core configurations
        self.database = DatabaseConfig()
        self.ai = AIConfig()
        self.services = ServiceConfig()
        self.memory = MemoryConfig()
        self.security = SecurityConfig()
        self.monitoring = MonitoringConfig()
        
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Service settings
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8010"))
        self.workers = int(os.getenv("WORKERS", "1"))
        
        # Version info
        self.version = "1.0.0"
        self.build_id = os.getenv("BUILD_ID", "dev")
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors: List[str] = []
        
        # Check required API keys
        if not self.ai.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        
        # Check database connections
        if not self.database.postgres_password and self.environment == "production":
            errors.append("POSTGRES_PASSWORD is required in production")
        
        # Check service endpoints
        if not self.services.service_api_key and self.environment == "production":
            errors.append("SERVICE_API_KEY is required in production")
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def get_database_url(self) -> str:
        """Get PostgreSQL database URL"""
        return (
            f"postgresql://{self.database.postgres_user}:"
            f"{self.database.postgres_password}@"
            f"{self.database.postgres_host}:"
            f"{self.database.postgres_port}/"
            f"{self.database.postgres_db}"
        )
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        auth = f":{self.database.redis_password}@" if self.database.redis_password else ""
        return f"redis://{auth}{self.database.redis_host}:{self.database.redis_port}/{self.database.redis_db}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (for API responses)"""
        return {
            "version": self.version,
            "environment": self.environment,
            "debug": self.debug,
            "ai_model": self.ai.openai_model,
            "agent_name": self.ai.agent_name,
            "features": {
                "rate_limiting": self.security.enable_rate_limiting,
                "metrics": self.monitoring.enable_metrics,
                "health_checks": self.monitoring.enable_health_checks
            }
        }


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get global configuration instance"""
    return config


# Configuration validation on import
if not config.validate():
    print("Warning: Configuration validation failed. Some features may not work correctly.")

# Environment-specific settings
if config.environment == "production":
    # Production optimizations
    config.ai.openai_temperature = 0.3  # More deterministic responses
    config.memory.cleanup_interval = 1800  # More frequent cleanup
    config.monitoring.response_time_threshold = 1.0  # Stricter performance
elif config.environment == "development":
    # Development settings
    config.ai.openai_temperature = 0.7  # More creative responses
    config.debug = True
    config.monitoring.log_level = "DEBUG"