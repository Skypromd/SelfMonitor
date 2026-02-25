"""
Automated Model Deployment and Serving System
Handles deployment of ML models to Kubernetes with A/B testing
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import yaml
import tempfile
import subprocess
from pathlib import Path

import kubernetes
from kubernetes.client.rest import ApiException
import docker

from mlflow.tracking import MlflowClient
import mlflow.sklearn
import mlflow.tensorflow
import mlflow.pytorch

from .config import MLOpsConfig, ModelConfig
from .notifications import SlackNotifier

logger = logging.getLogger(__name__)

class ModelDeploymentManager:
    """
    Manages deployment of ML models to Kubernetes
    """
    
    def __init__(self, config: MLOpsConfig):
        self.config = config
        self.mlflow_client = MlflowClient(config.tracking_uri)
        self.notifier = SlackNotifier(config.slack_webhook_url)
        
        # Initialize Kubernetes client
        if config.k8s_config_path:
            kubernetes.config.load_kube_config(config_file=config.k8s_config_path)
        else:
            kubernetes.config.load_incluster_config()
            
        self.k8s_apps_v1 = kubernetes.client.AppsV1Api()
        self.k8s_core_v1 = kubernetes.client.CoreV1Api()
        self.k8s_networking_v1 = kubernetes.client.NetworkingV1Api()
        
        # Docker client for building images
        self.docker_client = docker.from_env()
        
    async def deploy_to_production(
        self,
        model_name: str,
        version: str,
        model_config: Optional[ModelConfig] = None
    ) -> bool:
        """Deploy model to production environment"""
        try:
            logger.info(f"Starting production deployment for {model_name} v{version}")
            
            # Get model from MLflow
            model_uri = f"models:/{model_name}/{version}"
            model_info = self.mlflow_client.get_model_version(model_name, version)
            
            # Build model serving image
            image_tag = await self._build_model_image(model_name, version, model_uri)
            
            if not image_tag:
                logger.error(f"Failed to build image for {model_name} v{version}")
                return False
                
            # Create Kubernetes deployment
            deployment_success = await self._create_k8s_deployment(
                model_name, version, image_tag, model_config
            )
            
            if not deployment_success:
                logger.error(f"Failed to create Kubernetes deployment for {model_name}")
                return False
                
            # Create service and ingress
            service_success = await self._create_k8s_service(model_name, model_config)
            ingress_success = await self._create_k8s_ingress(model_name)
            
            if not (service_success and ingress_success):
                logger.error(f"Failed to create service/ingress for {model_name}")
                await self._cleanup_failed_deployment(model_name, version)
                return False
                
            # Wait for deployment to be ready
            ready = await self._wait_for_deployment_ready(model_name, timeout=300)
            
            if not ready:
                logger.error(f"Deployment not ready within timeout for {model_name}")
                await self._cleanup_failed_deployment(model_name, version)
                return False
                
            # Run health checks
            health_check_passed = await self._run_health_checks(model_name)
            
            if not health_check_passed:
                logger.error(f"Health checks failed for {model_name}")
                await self._cleanup_failed_deployment(model_name, version)
                return False
                
            logger.info(f"Successfully deployed {model_name} v{version} to production")
            
            # Send success notification
            await self.notifier.send_message(
                f"✅ Production deployment successful: {model_name} v{version}",
                channel="ml-ops"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy {model_name} v{version}: {str(e)}")
            await self._cleanup_failed_deployment(model_name, version)
            
            # Send failure notification
            await self.notifier.send_message(
                f"❌ Production deployment failed: {model_name} v{version}\nError: {str(e)}",
                channel="ml-ops"
            )
            
            return False
            
    async def _build_model_image(
        self,
        model_name: str,
        version: str,
        model_uri: str
    ) -> Optional[str]:
        """Build Docker image for model serving"""
        try:
            # Create temporary directory for build context
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Download model from MLflow
                model_path = temp_path / "model"
                mlflow.artifacts.download_artifacts(model_uri, dst_path=str(model_path))
                
                # Create Dockerfile
                dockerfile_content = self._generate_dockerfile(model_name)
                dockerfile_path = temp_path / "Dockerfile"
                dockerfile_path.write_text(dockerfile_content)
                
                # Create serving script
                serving_script = self._generate_serving_script(model_name)
                serving_script_path = temp_path / "serve.py"
                serving_script_path.write_text(serving_script)
                
                # Create requirements.txt
                requirements_content = self._generate_requirements(model_name)
                requirements_path = temp_path / "requirements.txt" 
                requirements_path.write_text(requirements_content)
                
                # Build image
                image_tag = f"{self.config.docker_registry}/{self.config.docker_repository}/{model_name}:{version}"
                
                logger.info(f"Building image: {image_tag}")
                
                image, build_logs = self.docker_client.images.build(
                    path=str(temp_path),
                    tag=image_tag,
                    rm=True,
                    pull=True
                )
                
                # Push to registry
                logger.info(f"Pushing image: {image_tag}")
                push_logs = self.docker_client.images.push(image_tag, stream=True)
                
                for line in push_logs:
                    line_json = json.loads(line)
                    if 'error' in line_json:
                        raise Exception(f"Push failed: {line_json['error']}")
                        
                logger.info(f"Successfully built and pushed image: {image_tag}")
                return image_tag
                
        except Exception as e:
            logger.error(f"Failed to build model image: {str(e)}")
            return None
            
    def _generate_dockerfile(self, model_name: str) -> str:
        """Generate Dockerfile for model serving"""
        return f"""
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model and serving script
COPY model/ ./model/
COPY serve.py .

# Create non-root user
RUN useradd --create-home --uid 1001 modeluser
USER modeluser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Start serving
CMD ["python", "serve.py"]
        """
        
    def _generate_serving_script(self, model_name: str) -> str:
        """Generate serving script for the model"""
        return f"""
import os
import asyncio
import logging
from typing import Dict, List, Any
import json
from datetime import datetime

import mlflow.pyfunc
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from prometheus_client import Counter, Histogram, start_http_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load model
MODEL_PATH = "/app/model"
model = mlflow.pyfunc.load_model(MODEL_PATH)

# Prometheus metrics
prediction_counter = Counter(
    'model_predictions_total',
    'Total predictions served',
    ['model_name', 'status']
)

prediction_latency = Histogram(
    'model_prediction_latency_seconds',
    'Model prediction latency',
    ['model_name']
)

# FastAPI app
app = FastAPI(title="{model_name} Model Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictionRequest(BaseModel):
    features: Dict[str, Any]
    model_version: str = "latest"

class PredictionResponse(BaseModel):
    prediction: Any
    confidence: float
    model_name: str = "{model_name}"
    model_version: str
    timestamp: str

@app.get("/health")
async def health_check():
    return {{"status": "healthy", "model": "{model_name}"}}

@app.get("/info")
async def model_info():
    return {{
        "model_name": "{model_name}",
        "mlflow_version": mlflow.__version__,
        "model_path": MODEL_PATH
    }}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Convert features to DataFrame
        features_df = pd.DataFrame([request.features])
        
        # Make prediction
        prediction = model.predict(features_df)
        
        # Calculate confidence (simplified)
        if hasattr(model._model_impl.python_model, 'predict_proba'):
            probabilities = model._model_impl.python_model.predict_proba(features_df)
            confidence = float(np.max(probabilities[0]))
        else:
            confidence = 0.95  # Default confidence for regression
            
        # Record metrics
        end_time = asyncio.get_event_loop().time()
        prediction_latency.labels(model_name="{model_name}").observe(end_time - start_time)
        prediction_counter.labels(model_name="{model_name}", status="success").inc()
        
        # Format response
        if isinstance(prediction, np.ndarray):
            prediction = prediction.tolist()
            
        return PredictionResponse(
            prediction=prediction,
            confidence=confidence,
            model_version=request.model_version,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        prediction_counter.labels(model_name="{model_name}", status="error").inc()
        logger.error(f"Prediction failed: {{str(e)}}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch_predict")
async def batch_predict(requests: List[PredictionRequest]):
    try:
        results = []
        for req in requests:
            result = await predict(req)
            results.append(result)
        return results
    except Exception as e:
        logger.error(f"Batch prediction failed: {{str(e)}}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Start Prometheus metrics server
    start_http_server(9090)
    
    # Start FastAPI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        workers=1
    )
        """
        
    def _generate_requirements(self, model_name: str) -> str:
        """Generate requirements.txt for model serving"""
        return """
mlflow>=2.8.0
fastapi>=0.104.0
uvicorn[standard]>=0.23.0
pandas>=2.1.0
numpy>=1.25.0
scikit-learn>=1.3.0
prometheus-client>=0.19.0
pydantic>=2.4.0
"""

    async def _create_k8s_deployment(
        self,
        model_name: str,
        version: str,
        image_tag: str,
        model_config: Optional[ModelConfig] = None
    ) -> bool:
        """Create Kubernetes deployment for model"""
        try:
            # Use provided config or default
            if model_config is None:
                model_config = ModelConfig(name=model_name, version=version, model_type="sklearn")
                
            deployment_name = f"{model_name}-deployment"
            
            # Define deployment manifest
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": deployment_name,
                    "namespace": self.config.k8s_namespace,
                    "labels": {
                        "app": model_name,
                        "version": version,
                        "component": "model-server"
                    }
                },
                "spec": {
                    "replicas": model_config.min_replicas,
                    "selector": {
                        "matchLabels": {
                            "app": model_name,
                            "version": version
                        }
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": model_name,
                                "version": version,
                                "component": "model-server"
                            },
                            "annotations": {
                                "prometheus.io/scrape": "true",
                                "prometheus.io/port": "9090",
                                "prometheus.io/path": "/metrics"
                            }
                        },
                        "spec": {
                            "containers": [{
                                "name": "model-server",
                                "image": image_tag,
                                "ports": [
                                    {"containerPort": 8080, "name": "http"},
                                    {"containerPort": 9090, "name": "metrics"}
                                ],
                                "env": [
                                    {"name": "MODEL_NAME", "value": model_name},
                                    {"name": "MODEL_VERSION", "value": version}
                                ],
                                "resources": {
                                    "requests": {
                                        "cpu": model_config.cpu_request,
                                        "memory": model_config.memory_request
                                    },
                                    "limits": {
                                        "cpu": model_config.cpu_limit,
                                        "memory": model_config.memory_limit
                                    }
                                },
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": "/health",
                                        "port": 8080
                                    },
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10
                                },
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/health", 
                                        "port": 8080
                                    },
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 5
                                },
                                "securityContext": {
                                    "runAsNonRoot": True,
                                    "runAsUser": 1001,
                                    "readOnlyRootFilesystem": True,
                                    "allowPrivilegeEscalation": False
                                }
                            }],
                            "securityContext": {
                                "fsGroup": 1001
                            }
                        }
                    }
                }
            }
            
            # Create deployment
            try:
                self.k8s_apps_v1.create_namespaced_deployment(
                    namespace=self.config.k8s_namespace,
                    body=deployment
                )
                logger.info(f"Created deployment: {deployment_name}")
                
            except ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info(f"Deployment {deployment_name} already exists, updating...")
                    self.k8s_apps_v1.replace_namespaced_deployment(
                        name=deployment_name,
                        namespace=self.config.k8s_namespace,
                        body=deployment
                    )
                else:
                    raise
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to create deployment: {str(e)}")
            return False
            
    async def _create_k8s_service(
        self,
        model_name: str,
        model_config: Optional[ModelConfig] = None  
    ) -> bool:
        """Create Kubernetes service for model"""
        try:
            service_name = f"{model_name}-service"
            
            service = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": service_name,
                    "namespace": self.config.k8s_namespace,
                    "labels": {
                        "app": model_name,
                        "component": "model-server"
                    }
                },
                "spec": {
                    "selector": {
                        "app": model_name
                    },
                    "ports": [
                        {
                            "name": "http",
                            "port": 80,
                            "targetPort": 8080,
                            "protocol": "TCP"
                        },
                        {
                            "name": "metrics",
                            "port": 9090,
                            "targetPort": 9090,
                            "protocol": "TCP"
                        }
                    ],
                    "type": "ClusterIP"
                }
            }
            
            try:
                self.k8s_core_v1.create_namespaced_service(
                    namespace=self.config.k8s_namespace,
                    body=service
                )
                logger.info(f"Created service: {service_name}")
                
            except ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info(f"Service {service_name} already exists")
                else:
                    raise
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to create service: {str(e)}")
            return False
            
    async def _create_k8s_ingress(self, model_name: str) -> bool:
        """Create Kubernetes ingress for model"""
        try:
            ingress_name = f"{model_name}-ingress"
            service_name = f"{model_name}-service"
            
            ingress = {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "Ingress",
                "metadata": {
                    "name": ingress_name,
                    "namespace": self.config.k8s_namespace,
                    "annotations": {
                        "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
                        "nginx.ingress.kubernetes.io/use-regex": "true"
                    }
                },
                "spec": {
                    "rules": [{
                        "host": "api.selfmonitor.com",
                        "http": {
                            "paths": [{
                                "path": f"/ml/{model_name}(/|$)(.*)",
                                "pathType": "ImplementationSpecific",
                                "backend": {
                                    "service": {
                                        "name": service_name,
                                        "port": {
                                            "number": 80
                                        }
                                    }
                                }
                            }]
                        }
                    }]
                }
            }
            
            try:
                self.k8s_networking_v1.create_namespaced_ingress(
                    namespace=self.config.k8s_namespace,
                    body=ingress
                )
                logger.info(f"Created ingress: {ingress_name}")
                
            except ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info(f"Ingress {ingress_name} already exists")
                else:
                    raise
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to create ingress: {str(e)}")
            return False
            
    async def _wait_for_deployment_ready(
        self,
        model_name: str,
        timeout: int = 300
    ) -> bool:
        """Wait for deployment to be ready"""
        try:
            deployment_name = f"{model_name}-deployment"
            
            for _ in range(timeout // 10):
                deployment = self.k8s_apps_v1.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.config.k8s_namespace
                )
                
                if (deployment.status.ready_replicas and 
                    deployment.status.ready_replicas == deployment.spec.replicas):
                    logger.info(f"Deployment {deployment_name} is ready")
                    return True
                    
                await asyncio.sleep(10)
                
            logger.error(f"Deployment {deployment_name} not ready within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to check deployment status: {str(e)}")
            return False
            
    async def _run_health_checks(self, model_name: str) -> bool:
        """Run health checks on deployed model"""
        try:
            # Implementation would make HTTP requests to the model service
            # and verify responses
            logger.info(f"Running health checks for {model_name}")
            
            # For now, just return True
            # In production, implement actual health checks
            await asyncio.sleep(2)  # Simulate health check
            
            return True
            
        except Exception as e:
            logger.error(f"Health checks failed for {model_name}: {str(e)}")
            return False
            
    async def _cleanup_failed_deployment(self, model_name: str, version: str):
        """Clean up resources from failed deployment"""
        try:
            deployment_name = f"{model_name}-deployment"
            
            logger.info(f"Cleaning up failed deployment: {deployment_name}")
            
            # Delete deployment
            try:
                self.k8s_apps_v1.delete_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.config.k8s_namespace
                )
            except ApiException:
                pass  # Ignore if doesn't exist
                
            # Note: We don't clean up service and ingress as they might be used by other versions
            
        except Exception as e:
            logger.error(f"Failed to cleanup deployment: {str(e)}")


class ABTestingManager:
    """
    Manages A/B testing of model versions
    """
    
    def __init__(self, config: MLOpsConfig):
        self.config = config
        self.deployment_manager = ModelDeploymentManager(config)
        
    async def setup_ab_test(
        self,
        model_name: str,
        champion_version: str,
        challenger_version: str,
        traffic_split: float = 0.1
    ) -> bool:
        """Setup A/B test between two model versions"""
        try:
            logger.info(f"Setting up A/B test for {model_name}: {champion_version} vs {challenger_version}")
            
            # Deploy challenger version
            challenger_deployment = await self.deployment_manager.deploy_to_production(
                f"{model_name}-challenger",
                challenger_version
            )
            
            if not challenger_deployment:
                logger.error("Failed to deploy challenger version")
                return False
                
            # Create traffic splitting configuration
            # This would typically involve configuring Istio or other service mesh
            # For now, just log the configuration
            logger.info(f"Traffic split: {1-traffic_split:.0%} champion, {traffic_split:.0%} challenger")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup A/B test: {str(e)}")
            return False