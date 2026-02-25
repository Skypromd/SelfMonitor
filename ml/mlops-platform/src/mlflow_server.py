"""
MLflow Tracking Server and Model Registry
Centralized ML lifecycle management for SelfMonitor platform
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

# External dependencies with fallbacks
try:
    import mlflow  # type: ignore[import-untyped]
    import mlflow.tracking  # type: ignore[import-untyped]
    from mlflow.tracking import MlflowClient  # type: ignore[import-untyped]
    from mlflow.models import infer_signature  # type: ignore[import-untyped]
    from mlflow.store.artifact.s3_artifact_repo import S3ArtifactRepository  # type: ignore[import-untyped]
    _has_mlflow = True
except ImportError:
    _has_mlflow = False
    
    class MlflowClient:  # type: ignore[misc]
        def __init__(self, tracking_uri: Optional[str] = None): pass
        def create_experiment(self, *args: Any, **kwargs: Any) -> str: return "mock_experiment_id"
    
    class MockMLflow:
        def set_tracking_uri(self, *args: Any, **kwargs: Any) -> None: pass
        def start_run(self, *args: Any, **kwargs: Any) -> Any: return self
        def log_param(self, *args: Any, **kwargs: Any) -> None: pass
        def log_metric(self, *args: Any, **kwargs: Any) -> None: pass
        def set_tag(self, *args: Any, **kwargs: Any) -> None: pass
        def log_artifact(self, *args: Any, **kwargs: Any) -> None: pass
        def __enter__(self) -> Any: return self
        def __exit__(self, *args: Any) -> None: pass
        def __init__(self) -> None:
            self.sklearn = MockMLflowSklearn()
    
    class MockMLflowSklearn:
        def log_model(self, *args: Any, **kwargs: Any) -> None: pass
    
    def infer_signature(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        return {"inputs": [], "outputs": []}
    
    class S3ArtifactRepository:  # type: ignore[misc]
        pass
    
    mlflow = MockMLflow()  # type: ignore[misc]

try:
    import pandas as pd  # type: ignore[import-untyped]
    import numpy as np  # type: ignore[import-untyped]
except ImportError:
    pd = None  # type: ignore[misc]
    np = None  # type: ignore[misc]

try:
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score  # type: ignore[import-untyped]
except ImportError:
    def accuracy_score(*args: Any, **kwargs: Any) -> float: return 0.0  # type: ignore[misc]
    def precision_score(*args: Any, **kwargs: Any) -> float: return 0.0  # type: ignore[misc]  
    def recall_score(*args: Any, **kwargs: Any) -> float: return 0.0  # type: ignore[misc]
    def f1_score(*args: Any, **kwargs: Any) -> float: return 0.0  # type: ignore[misc]

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server  # type: ignore[import-untyped]
except ImportError:
    # Fallback prometheus classes
    class Counter:  # type: ignore[misc]
        def __init__(self, *args: Any, **kwargs: Any): pass
        def labels(self, *args: Any, **kwargs: Any) -> 'Counter': return self
        def inc(self, *args: Any) -> None: pass
    
    class Histogram:  # type: ignore[misc]
        def __init__(self, *args: Any, **kwargs: Any): pass
        def observe(self, *args: Any) -> None: pass
        def time(self) -> Any:
            class TimerContext:
                def __enter__(self) -> None: pass
                def __exit__(self, *args: Any) -> None: pass
            return TimerContext()
    
    class Gauge:  # type: ignore[misc] 
        def __init__(self, *args: Any, **kwargs: Any): pass
        def labels(self, *args: Any, **kwargs: Any) -> 'Gauge': return self
        def set(self, *args: Any) -> None: pass
    
    def start_http_server(*args: Any, **kwargs: Any) -> None:  # type: ignore[misc]
        pass

try:
    import boto3  # type: ignore[import-untyped]
except ImportError:
    class MockBoto3:  # type: ignore[misc]
        def client(self, *args: Any, **kwargs: Any) -> Any: return {}
    boto3 = MockBoto3()  # type: ignore[misc]

try:
    from minio import Minio  # type: ignore[import-untyped]
except ImportError:
    class Minio:  # type: ignore[misc]
        def __init__(self, *args: Any, **kwargs: Any): pass

try:
    import redis  # type: ignore[import-untyped]
    import asyncpg  # type: ignore[import-untyped]
except ImportError:
    redis = None  # type: ignore[misc]
    asyncpg = None  # type: ignore[misc]

from utils.config import MLOpsConfig
from utils.monitoring import MetricsCollector
from utils.deployment import ModelDeploymentManager
from utils.notifications import SlackNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus Metrics
model_training_duration: Any = Histogram(  # type: ignore[misc]
    'mlflow_model_training_duration_seconds',
    'Time spent training models',
    ['model_type', 'experiment_id']
)

model_deployment_counter: Any = Counter(  # type: ignore[misc]
    'mlflow_model_deployments_total',
    'Number of model deployments',
    ['model_name', 'stage', 'status']
)

active_models_gauge: Any = Gauge(  # type: ignore[misc]
    'mlflow_active_models',
    'Number of active models in production',
    ['service_name']
)

model_performance_gauge: Any = Gauge(  # type: ignore[misc]
    'mlflow_model_performance',
    'Model performance metrics',
    ['model_name', 'metric_name']
)

class MLflowTrackingServer:
    """
    MLflow Tracking Server for experiment management and model registry
    """
    
    def __init__(self, config: MLOpsConfig):
        self.config = config
        self.client: Any = MlflowClient(config.tracking_uri)  # type: ignore[misc]
        self.metrics_collector = MetricsCollector(config)
        self.deployment_manager = ModelDeploymentManager(config)
        self.notifier = SlackNotifier(config.slack_webhook_url)
        
        # Set MLflow tracking URI
        mlflow.set_tracking_uri(config.tracking_uri)  # type: ignore[misc]
        
        # Initialize storage backends
        self._init_storage()
        
    def _init_storage(self):
        """Initialize artifact storage backends"""
        if self.config.artifact_store == "s3":
            self.s3_client: Any = boto3.client(  # type: ignore[misc]
                's3',
                endpoint_url=self.config.s3_endpoint,
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key
            )
        elif self.config.artifact_store == "minio":
            self.minio_client: Any = Minio(  # type: ignore[misc]
                self.config.minio_endpoint,
                access_key=self.config.minio_access_key,
                secret_key=self.config.minio_secret_key,
                secure=self.config.minio_secure
            )
            
    async def create_experiment(
        self,
        name: str,
        artifact_location: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a new MLflow experiment"""
        try:
            experiment_id: str = self.client.create_experiment(  # type: ignore[misc]
                name=name,
                artifact_location=artifact_location,
                tags=tags or {}
            )
            
            logger.info(f"Created experiment: {name} (ID: {experiment_id})")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to create experiment {name}: {str(e)}")
            raise
            
    async def log_model_training(
        self,
        experiment_id: str,
        model_name: str,
        model: Any,
        training_data: Any,  # pd.DataFrame
        validation_data: Any,  # pd.DataFrame
        parameters: Dict[str, Any],
        metrics: Dict[str, float],
        artifacts: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Log model training run with MLflow"""
        
        with mlflow.start_run(experiment_id=experiment_id, run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:  # type: ignore[misc]
            
            # Log parameters
            for key, value in parameters.items():
                mlflow.log_param(key, value)  # type: ignore[misc]
                
            # Log metrics
            for key, value in metrics.items():
                mlflow.log_metric(key, value)  # type: ignore[misc]
                model_performance_gauge.labels(  # type: ignore[misc]
                    model_name=model_name,
                    metric_name=key
                ).set(value)  # type: ignore[misc]
                
            # Log tags
            if tags:
                for key, value in tags.items():
                    mlflow.set_tag(key, value)  # type: ignore[misc]
                    
            # Infer model signature
            signature: Any = infer_signature(training_data, model.predict(training_data[:5]))  # type: ignore[misc]
            
            # Log model
            mlflow.sklearn.log_model(  # type: ignore[misc]
                sk_model=model,
                artifact_path="model",
                signature=signature,
                registered_model_name=model_name
            )
            
            # Log artifacts
            if artifacts:
                for artifact_name, artifact_path in artifacts.items():
                    mlflow.log_artifact(artifact_path, artifact_name)  # type: ignore[misc]
                    
            # Log dataset info
            mlflow.log_param("training_samples", len(training_data))  # type: ignore[misc]
            mlflow.log_param("validation_samples", len(validation_data))  # type: ignore[misc]
            mlflow.log_param("feature_count", training_data.shape[1])  # type: ignore[misc,attr-defined]
            
            run_id: str = str(run.info.run_id)  # type: ignore[misc,attr-defined]
            logger.info(f"Logged training run for {model_name}: {run_id}")
            
            # Update Prometheus metrics
            model_training_duration.labels(
                model_type=model_name,
                experiment_id=experiment_id
            ).observe(time.time() - run.info.start_time / 1000)  # type: ignore[misc,attr-defined]
            
            return run_id
            
    async def register_model_version(
        self,
        model_name: str,
        run_id: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Register a new model version"""
        try:
            model_uri = f"runs:/{run_id}/model"
            model_version = self.client.create_model_version(
                name=model_name,
                source=model_uri,
                run_id=run_id,
                description=description,
                tags=tags
            )
            
            version_number = model_version.version
            logger.info(f"Registered {model_name} version {version_number}")
            
            # Send notification
            await self.notifier.send_message(
                f"🤖 New model version registered: {model_name} v{version_number}",
                channel="ml-ops"
            )
            
            return version_number
            
        except Exception as e:
            logger.error(f"Failed to register model {model_name}: {str(e)}")
            raise
            
    async def promote_model_to_staging(
        self,
        model_name: str,
        version: str,
        archive_existing_versions: bool = True
    ) -> bool:
        """Promote model version to Staging"""
        try:
            # Archive existing staging versions if requested
            if archive_existing_versions:
                staging_versions = self.client.get_latest_versions(
                    model_name,
                    stages=["Staging"]
                )
                for model_version in staging_versions:
                    self.client.transition_model_version_stage(
                        name=model_name,
                        version=model_version.version,
                        stage="Archived"
                    )
                    
            # Promote to staging
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage="Staging",
                archive_existing_versions=archive_existing_versions
            )
            
            logger.info(f"Promoted {model_name} v{version} to Staging")
            
            model_deployment_counter.labels(
                model_name=model_name,
                stage="staging",
                status="success"
            ).inc()
            
            # Send notification
            await self.notifier.send_message(
                f"🚀 Model promoted to Staging: {model_name} v{version}",
                channel="ml-ops"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote {model_name} v{version} to staging: {str(e)}")
            model_deployment_counter.labels(
                model_name=model_name,
                stage="staging", 
                status="failed"
            ).inc()
            return False
            
    async def promote_model_to_production(
        self,
        model_name: str,
        version: str,
        approval_required: bool = True
    ) -> bool:
        """Promote model version to Production"""
        try:
            # Check if approval is required and model is in staging
            if approval_required:
                model_version = self.client.get_model_version(model_name, version)
                if model_version.current_stage != "Staging":
                    raise ValueError("Model must be in Staging before production deployment")
                    
            # Archive existing production versions
            production_versions = self.client.get_latest_versions(
                model_name,
                stages=["Production"]
            )
            for model_version in production_versions:
                self.client.transition_model_version_stage(
                    name=model_name,
                    version=model_version.version,
                    stage="Archived"
                )
                
            # Promote to production
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage="Production"
            )
            
            logger.info(f"Promoted {model_name} v{version} to Production")
            
            # Deploy to serving infrastructure
            deployment_success = await self.deployment_manager.deploy_to_production(
                model_name, version
            )
            
            if deployment_success:
                model_deployment_counter.labels(
                    model_name=model_name,
                    stage="production",
                    status="success"
                ).inc()
                
                # Update active models gauge
                active_models_gauge.labels(service_name=model_name).inc()
                
                # Send notification
                await self.notifier.send_message(
                    f"🎉 Model deployed to Production: {model_name} v{version}",
                    channel="ml-ops"
                )
                
                return True
            else:
                # Rollback stage transition on deployment failure
                self.client.transition_model_version_stage(
                    name=model_name,
                    version=version,
                    stage="Staging"
                )
                
                model_deployment_counter.labels(
                    model_name=model_name,
                    stage="production",
                    status="failed"
                ).inc()
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to promote {model_name} v{version} to production: {str(e)}")
            return False
            
    async def get_model_performance(
        self,
        model_name: str,
        stage: str = "Production",
        days: int = 30
    ) -> Dict[str, Any]:
        """Get model performance metrics"""
        try:
            # Get latest model version in specified stage
            latest_versions = self.client.get_latest_versions(
                model_name,
                stages=[stage]
            )
            
            if not latest_versions:
                return {"error": f"No {stage} version found for {model_name}"}
                
            model_version = latest_versions[0]
            
            # Get run metrics
            run_id = model_version.run_id
            run = self.client.get_run(run_id)
            
            # Get recent performance metrics from monitoring
            recent_metrics = await self.metrics_collector.get_model_metrics(
                model_name,
                days=days
            )
            
            return {
                "model_name": model_name,
                "version": model_version.version,
                "stage": stage,
                "creation_timestamp": model_version.creation_timestamp,
                "training_metrics": run.data.metrics,
                "recent_performance": recent_metrics,
                "status": model_version.status
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance for {model_name}: {str(e)}")
            return {"error": str(e)}
            
    async def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments"""
        try:
            experiments = self.client.search_experiments()
            return [
                {
                    "experiment_id": exp.experiment_id,
                    "name": exp.name,
                    "artifact_location": exp.artifact_location,
                    "lifecycle_stage": exp.lifecycle_stage,
                    "tags": exp.tags
                }
                for exp in experiments
            ]
        except Exception as e:
            logger.error(f"Failed to list experiments: {str(e)}")
            return []
            
    async def list_registered_models(self) -> List[Dict[str, Any]]:
        """List all registered models"""
        try:
            models = self.client.search_registered_models()  # type: ignore[misc]
            model_list: List[Dict[str, Any]] = []
            
            for model in models:
                # Get latest versions for each stage
                latest_versions = {}
                all_versions = self.client.get_latest_versions(
                    model.name,
                    stages=["Staging", "Production", "Archived"]
                )
                
                for version in all_versions:
                    latest_versions[version.current_stage] = {
                        "version": version.version,
                        "creation_timestamp": version.creation_timestamp,
                        "status": version.status
                    }
                    
                model_list.append({  # type: ignore[misc]
                    "name": model.name,
                    "description": model.description,
                    "tags": model.tags,
                    "latest_versions": latest_versions,
                    "creation_timestamp": model.creation_timestamp
                })
                
            return model_list
            
        except Exception as e:
            logger.error(f"Failed to list registered models: {str(e)}")
            return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mlflow_server
    config = MLOpsConfig()
    mlflow_server = MLflowTrackingServer(config)
    
    # Start Prometheus metrics server
    start_http_server(8000)
    
    logger.info("MLOps Platform started successfully")
    
    yield
    
    # Shutdown
    logger.info("MLOps Platform shutting down")

# FastAPI Application
app = FastAPI(
    title="SelfMonitor MLOps Platform",
    description="MLflow-based ML lifecycle management",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MLflow server instance
mlflow_server: MLflowTrackingServer = None  # type: ignore[assignment]

# Pydantic Models
class ExperimentCreate(BaseModel):
    name: str
    artifact_location: Optional[str] = None
    tags: Optional[Dict[str, str]] = None

class ModelTraining(BaseModel):
    experiment_id: str
    model_name: str
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    tags: Optional[Dict[str, str]] = None

class ModelPromotion(BaseModel):
    model_name: str
    version: str
    archive_existing: bool = True

# API Endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/experiments")
async def create_experiment(experiment: ExperimentCreate):
    """Create new MLflow experiment"""
    experiment_id = await mlflow_server.create_experiment(
        name=experiment.name,
        artifact_location=experiment.artifact_location,
        tags=experiment.tags
    )
    return {"experiment_id": experiment_id}

@app.get("/experiments")
async def list_experiments():
    """List all experiments"""
    return await mlflow_server.list_experiments()

@app.get("/models")
async def list_models():
    """List all registered models"""
    return await mlflow_server.list_registered_models()

@app.post("/models/{model_name}/promote/staging")
async def promote_to_staging(
    model_name: str,
    promotion: ModelPromotion,
    background_tasks: BackgroundTasks
):
    """Promote model to staging"""
    background_tasks.add_task(
        mlflow_server.promote_model_to_staging,
        promotion.model_name,
        promotion.version,
        promotion.archive_existing
    )
    return {"message": f"Promoting {model_name} v{promotion.version} to staging"}

@app.post("/models/{model_name}/promote/production")
async def promote_to_production(
    model_name: str,
    promotion: ModelPromotion,
    background_tasks: BackgroundTasks
):
    """Promote model to production"""
    background_tasks.add_task(
        mlflow_server.promote_model_to_production,
        promotion.model_name,
        promotion.version
    )
    return {"message": f"Promoting {model_name} v{promotion.version} to production"}

@app.get("/models/{model_name}/performance")
async def get_model_performance(
    model_name: str,
    stage: str = "Production",
    days: int = 30
):
    """Get model performance metrics"""
    performance = await mlflow_server.get_model_performance(
        model_name, stage, days
    )
    return performance

if __name__ == "__main__":
    uvicorn.run(  # type: ignore[misc]
        "mlflow_server:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        workers=1
    )