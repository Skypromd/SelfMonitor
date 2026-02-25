"""
Configuration management for MLOps Platform
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class MLOpsConfig:
    """Configuration for MLOps Platform"""
    
    # MLflow Configuration
    tracking_uri: str = field(default_factory=lambda: os.getenv(
        "MLFLOW_TRACKING_URI", 
        "postgresql://mlflow:mlflow@postgres:5432/mlflow"
    ))
    
    artifact_store: str = field(default_factory=lambda: os.getenv(
        "MLFLOW_ARTIFACT_STORE", 
        "s3"
    ))
    
    # S3/MinIO Configuration 
    s3_endpoint: Optional[str] = field(default_factory=lambda: os.getenv("S3_ENDPOINT"))
    aws_access_key: str = field(default_factory=lambda: os.getenv("AWS_ACCESS_KEY_ID", ""))
    aws_secret_key: str = field(default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY", ""))
    s3_bucket_name: str = field(default_factory=lambda: os.getenv("S3_BUCKET_NAME", "selfmonitor-ml-artifacts"))
    
    minio_endpoint: str = field(default_factory=lambda: os.getenv("MINIO_ENDPOINT", "minio:9000"))
    minio_access_key: str = field(default_factory=lambda: os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
    minio_secret_key: str = field(default_factory=lambda: os.getenv("MINIO_SECRET_KEY", "minioadmin"))
    minio_secure: bool = field(default_factory=lambda: os.getenv("MINIO_SECURE", "false").lower() == "true")
    
    # Database Configuration
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", "postgres"))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "mlflow"))
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", "mlflow"))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", "mlflow"))
    
    # Redis Configuration for Caching
    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "redis"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    redis_db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    
    # Monitoring Configuration
    prometheus_gateway: str = field(default_factory=lambda: os.getenv(
        "PROMETHEUS_GATEWAY", "prometheus-pushgateway:9091"
    ))
    
    grafana_url: str = field(default_factory=lambda: os.getenv(
        "GRAFANA_URL", "http://grafana:3000"
    ))
    
    # Model Serving Configuration
    model_serving_host: str = field(default_factory=lambda: os.getenv("MODEL_SERVING_HOST", "0.0.0.0"))
    model_serving_port: int = field(default_factory=lambda: int(os.getenv("MODEL_SERVING_PORT", "8080")))
    
    # Kubernetes Configuration
    k8s_namespace: str = field(default_factory=lambda: os.getenv("K8S_NAMESPACE", "selfmonitor"))
    k8s_config_path: Optional[str] = field(default_factory=lambda: os.getenv("KUBECONFIG"))
    
    # Model Deployment
    seldon_namespace: str = field(default_factory=lambda: os.getenv("SELDON_NAMESPACE", "seldon-system"))
    kserve_namespace: str = field(default_factory=lambda: os.getenv("KSERVE_NAMESPACE", "kserve"))
    
    # Container Registry
    docker_registry: str = field(default_factory=lambda: os.getenv("DOCKER_REGISTRY", "registry.selfmonitor.com"))
    docker_repository: str = field(default_factory=lambda: os.getenv("DOCKER_REPOSITORY", "ml-models"))
    
    # Notification Configuration
    slack_webhook_url: Optional[str] = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL"))
    slack_channel: str = field(default_factory=lambda: os.getenv("SLACK_CHANNEL", "#ml-ops"))
    
    email_smtp_server: Optional[str] = field(default_factory=lambda: os.getenv("EMAIL_SMTP_SERVER"))
    email_smtp_port: int = field(default_factory=lambda: int(os.getenv("EMAIL_SMTP_PORT", "587")))
    email_username: Optional[str] = field(default_factory=lambda: os.getenv("EMAIL_USERNAME"))
    email_password: Optional[str] = field(default_factory=lambda: os.getenv("EMAIL_PASSWORD"))
    
    # Security
    jwt_secret_key: str = field(default_factory=lambda: os.getenv(
        "JWT_SECRET_KEY", "your-super-secret-mlops-key-change-in-production"
    ))
    
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("MLOPS_API_KEY"))
    
    # Model Training Configuration
    default_experiment_name: str = field(default_factory=lambda: os.getenv(
        "DEFAULT_EXPERIMENT_NAME", "SelfMonitor_Default"
    ))
    
    max_parallel_training_jobs: int = field(default_factory=lambda: int(os.getenv(
        "MAX_PARALLEL_TRAINING_JOBS", "3"
    )))
    
    training_timeout_minutes: int = field(default_factory=lambda: int(os.getenv(
        "TRAINING_TIMEOUT_MINUTES", "120"
    )))
    
    # Model Registry Configuration
    auto_promote_threshold: float = field(default_factory=lambda: float(os.getenv(
        "AUTO_PROMOTE_THRESHOLD", "0.85"
    )))
    
    model_approval_required: bool = field(default_factory=lambda: os.getenv(
        "MODEL_APPROVAL_REQUIRED", "true"
    ).lower() == "true")
    
    # Data Drift Detection
    drift_detection_enabled: bool = field(default_factory=lambda: os.getenv(
        "DRIFT_DETECTION_ENABLED", "true"
    ).lower() == "true")
    
    drift_threshold: float = field(default_factory=lambda: float(os.getenv(
        "DRIFT_THRESHOLD", "0.1"
    )))
    
    # Performance Monitoring
    performance_monitoring_enabled: bool = field(default_factory=lambda: os.getenv(
        "PERFORMANCE_MONITORING_ENABLED", "true"
    ).lower() == "true")
    
    performance_degradation_threshold: float = field(default_factory=lambda: float(os.getenv(
        "PERFORMANCE_DEGRADATION_THRESHOLD", "0.05"
    )))
    
    # Feature Store Configuration
    feature_store_enabled: bool = field(default_factory=lambda: os.getenv(
        "FEATURE_STORE_ENABLED", "true"
    ).lower() == "true")
    
    feast_repo_path: str = field(default_factory=lambda: os.getenv(
        "FEAST_REPO_PATH", "/opt/feast"
    ))
    
    # A/B Testing Configuration  
    ab_testing_enabled: bool = field(default_factory=lambda: os.getenv(
        "AB_TESTING_ENABLED", "true"
    ).lower() == "true")
    
    ab_testing_traffic_split: float = field(default_factory=lambda: float(os.getenv(
        "AB_TESTING_TRAFFIC_SPLIT", "0.1"
    )))
    
    # Environment
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()
        
    def _validate_config(self):
        """Validate configuration parameters"""
        if not self.tracking_uri:
            raise ValueError("MLflow tracking URI must be specified")
            
        if self.artifact_store not in ["s3", "minio", "local"]:
            raise ValueError("Artifact store must be one of: s3, minio, local")
            
        if self.auto_promote_threshold < 0 or self.auto_promote_threshold > 1:
            raise ValueError("Auto promote threshold must be between 0 and 1")
            
        if self.drift_threshold < 0 or self.drift_threshold > 1:
            raise ValueError("Drift threshold must be between 0 and 1")
            
        if self.performance_degradation_threshold < 0:
            raise ValueError("Performance degradation threshold must be positive")
            
    @property
    def database_url(self) -> str:
        """Get database connection URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
        
    @property
    def artifact_uri(self) -> str:
        """Get artifact storage URI"""
        if self.artifact_store == "s3":
            return f"s3://{self.s3_bucket_name}/artifacts"
        elif self.artifact_store == "minio":
            return f"s3://{self.s3_bucket_name}/artifacts"
        else:
            return "./mlruns"
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "tracking_uri": self.tracking_uri,
            "artifact_store": self.artifact_store,
            "artifact_uri": self.artifact_uri,
            "database_url": self.database_url,
            "redis_url": self.redis_url,
            "environment": self.environment,
            "debug": self.debug,
            "model_approval_required": self.model_approval_required,
            "drift_detection_enabled": self.drift_detection_enabled,
            "performance_monitoring_enabled": self.performance_monitoring_enabled,
            "ab_testing_enabled": self.ab_testing_enabled
        }
        
# Model-specific configurations
@dataclass 
class ModelConfig:
    """Configuration for specific ML models"""
    name: str
    version: str
    model_type: str  # "sklearn", "tensorflow", "pytorch", "xgboost"
    
    # Resource requirements
    cpu_request: str = "100m"
    cpu_limit: str = "1000m"
    memory_request: str = "512Mi"
    memory_limit: str = "2Gi"
    
    # Scaling configuration
    min_replicas: int = 1
    max_replicas: int = 5
    target_cpu_utilization: int = 70
    
    # Model-specific parameters
    batch_size: int = 32
    timeout_seconds: int = 30
    
    # Monitoring thresholds
    accuracy_threshold: float = 0.8
    latency_threshold_ms: int = 100
    
    # Feature configuration
    features: Optional[Dict[str, Any]] = None
    preprocessing_steps: Optional[list] = None
    
# Service-specific model configurations
FRAUD_DETECTION_CONFIG = ModelConfig(
    name="fraud-detection",
    version="v1.0",
    model_type="xgboost",
    cpu_request="200m",
    cpu_limit="2000m", 
    memory_request="1Gi",
    memory_limit="4Gi",
    min_replicas=2,
    max_replicas=10,
    accuracy_threshold=0.95,
    latency_threshold_ms=50
)

RECOMMENDATION_CONFIG = ModelConfig(
    name="recommendation-engine",
    version="v1.0",
    model_type="pytorch",
    cpu_request="500m",
    cpu_limit="2000m",
    memory_request="2Gi", 
    memory_limit="8Gi",
    min_replicas=3,
    max_replicas=15,
    accuracy_threshold=0.75,
    latency_threshold_ms=200
)

CATEGORIZATION_CONFIG = ModelConfig(
    name="transaction-categorization",
    version="v1.0",
    model_type="tensorflow",
    cpu_request="100m",
    cpu_limit="1000m",
    memory_request="512Mi",
    memory_limit="2Gi",
    min_replicas=2,
    max_replicas=8,
    accuracy_threshold=0.85,
    latency_threshold_ms=100
)

AI_AGENT_CONFIG = ModelConfig(
    name="ai-agent",
    version="v1.0", 
    model_type="transformer",
    cpu_request="1000m",
    cpu_limit="4000m",
    memory_request="4Gi",
    memory_limit="16Gi",
    min_replicas=2,
    max_replicas=6,
    accuracy_threshold=0.8,
    latency_threshold_ms=500
)