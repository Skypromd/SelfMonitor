# SelfMonitor MLOps Platform

Complete ML Operations platform built with **MLflow**, providing end-to-end machine learning lifecycle management for the SelfMonitor FinTech platform.

## 🎯 Overview

The MLOps Platform manages the entire ML lifecycle for SelfMonitor's machine learning services:
- **Fraud Detection Models** - Real-time transaction fraud detection
- **Categorization Models** - Automatic transaction categorization
- **Recommendation Engine** - Personalized financial recommendations  
- **AI Agent Models** - Intelligent assistant capabilities

## 🏗️ Architecture

### Core Components

1. **MLflow Tracking Server** - Experiment management and model registry
2. **Automated Training Pipelines** - Scheduled model retraining
3. **Model Deployment System** - Kubernetes-based model serving
4. **Performance Monitoring** - Real-time model performance tracking
5. **Drift Detection** - Data and target drift monitoring
6. **A/B Testing Framework** - Model version comparison
7. **Notification System** - Multi-channel alerting (Slack, Email)

### Technology Stack

- **MLflow 2.8+** - ML lifecycle management
- **FastAPI** - REST API framework
- **PostgreSQL** - Experiment and metrics storage
- **MinIO/S3** - Model artifact storage
- **Redis** - Caching and session management
- **Prometheus** - Metrics collection
- **Kubernetes** - Container orchestration
- **Docker** - Containerization

## 🚀 Features

### Experiment Tracking
- **Automated Logging** - Parameters, metrics, artifacts, and models
- **Experiment Organization** - Hierarchical experiment structure
- **Version Control** - Complete model lineage tracking
- **Artifact Management** - Centralized storage of model artifacts

### Model Registry
- **Centralized Registry** - Single source of truth for models
- **Stage Management** - Development → Staging → Production workflow
- **Model Versioning** - Semantic versioning with rollback capabilities
- **Approval Workflows** - Manual or automated promotion gates

### Automated Training
- **Scheduled Training** - Daily automated model retraining
- **Hyperparameter Tuning** - Grid search optimization
- **Model Comparison** - Automatic selection of best performing models
- **Data Validation** - Quality checks before training

### Model Deployment  
- **Containerized Serving** - Docker-based model containers
- **Kubernetes Integration** - Auto-scaling model endpoints
- **Blue/Green Deployment** - Zero-downtime model updates
- **Canary Releases** - Gradual traffic shifting

### Performance Monitoring
- **Real-time Metrics** - Accuracy, latency, throughput tracking
- **Drift Detection** - Statistical tests for data/target drift
- **Alert System** - Proactive performance degradation alerts
- **Dashboard Integration** - Grafana visualization

### A/B Testing
- **Traffic Splitting** - Configurable traffic allocation
- **Statistical Testing** - Significance testing for model comparison
- **Automated Promotion** - Performance-based model promotion
- **Rollback Mechanisms** - Quick rollback on performance degradation

## 📊 Supported Models

### Fraud Detection Model
- **Type**: XGBoost/Random Forest binary classification
- **Features**: Transaction patterns, user behavior, account history
- **Accuracy Target**: >95%
- **Latency Target**: <50ms P95

### Transaction Categorization
- **Type**: Multi-class text classification
- **Features**: Merchant name, amount, transaction patterns
- **Accuracy Target**: >85%
- **Latency Target**: <100ms P95

### Recommendation Engine
- **Type**: Collaborative filtering + content-based
- **Features**: User profiles, financial goals, transaction history
- **Accuracy Target**: >75%
- **Latency Target**: <200ms P95

### AI Agent (SelfMate)
- **Type**: Transformer-based conversational AI
- **Features**: Financial context, user preferences, goal tracking
- **Accuracy Target**: >80%
- **Latency Target**: <500ms P95

## 🛠️ Development Setup

### Prerequisites
```bash
- Python 3.10+
- Docker & Docker Compose
- Kubernetes cluster (optional, for production)
```

### Local Development
```bash
# Clone repository
git clone <repository>
cd ml/mlops-platform

# Install dependencies
pip install -r requirements.txt

# Start infrastructure
docker-compose up -d postgres redis minio

# Start MLflow server
python src/mlflow_server.py

# Access MLflow UI
open http://localhost:5000
```

### Docker Compose Setup
```bash
# Start complete MLOps stack
docker-compose up -d mlflow-server

# Run training pipeline
docker-compose run --rm mlflow-server python scripts/training_pipeline.py

# View logs
docker-compose logs -f mlflow-server
```

## 📈 Usage Examples

### Model Training
```python
from mlops_platform.src.training_pipeline import TrainingPipeline
from mlops_platform.src.utils.config import MLOpsConfig

# Initialize pipeline
config = MLOpsConfig()
pipeline = TrainingPipeline(config)

# Train fraud detection model
success = await pipeline.run_fraud_detection_training()

# Train categorization model
success = await pipeline.run_categorization_training()
```

### Model Deployment
```python
from mlops_platform.src.utils.deployment import ModelDeploymentManager

# Deploy model to production
deployment_manager = ModelDeploymentManager(config)
success = await deployment_manager.deploy_to_production(
    model_name="fraud_detection",
    version="3"
)
```

### Performance Monitoring
```python
from mlops_platform.src.utils.monitoring import MetricsCollector

# Record model predictions
metrics = MetricsCollector(config)
await metrics.record_prediction(prediction)

# Calculate performance metrics
performance = await metrics.calculate_performance_metrics(
    model_name="fraud_detection",
    period="day"
)
```

### Drift Detection
```python
from mlops_platform.src.utils.monitoring import DriftDetector

# Initialize drift detector
drift_detector = DriftDetector(config)
await drift_detector.initialize_detector("fraud_detection", reference_data)

# Detect data drift
alert = await drift_detector.detect_data_drift(
    "fraud_detection", 
    current_data
)
```

## 🔧 Configuration

### Environment Variables
```env
# MLflow Configuration
MLFLOW_TRACKING_URI=postgresql://user:password@postgres:5432/mlflow
ARTIFACT_STORE=minio
S3_BUCKET_NAME=selfmonitor-ml-artifacts

# Storage Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Monitoring Configuration
REDIS_HOST=redis
PROMETHEUS_GATEWAY=prometheus-pushgateway:9091

# Model Configuration
AUTO_PROMOTE_THRESHOLD=0.85
DRIFT_THRESHOLD=0.1
PERFORMANCE_DEGRADATION_THRESHOLD=0.05

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
EMAIL_SMTP_SERVER=smtp.gmail.com
```

### Model Configuration
```python
from mlops_platform.src.utils.config import ModelConfig

# Fraud detection configuration
fraud_config = ModelConfig(
    name="fraud_detection",
    model_type="xgboost",
    cpu_request="200m",
    memory_request="1Gi",
    min_replicas=2,
    max_replicas=10,
    accuracy_threshold=0.95
)
```

## 🚀 Deployment

### Kubernetes Deployment
```bash
# Apply MLOps platform manifests
kubectl apply -f infra/k8s/mlops-platform.yaml

# Verify deployment
kubectl get pods -l component=ml-platform

# Access MLflow UI
kubectl port-forward svc/mlflow-server 5000:80
open http://localhost:5000
```

### Production Configuration
- **High Availability**: 3+ replicas with load balancing
- **Persistent Storage**: NFS/EFS for shared artifact storage
- **Security**: RBAC, network policies, secret management  
- **Monitoring**: Prometheus + Grafana dashboards
- **Backup**: Regular database and artifact backups

## 📊 Monitoring & Alerting

### Prometheus Metrics
```prometheus
# Model prediction metrics
model_predictions_total{model_name, status}
model_prediction_latency_seconds{model_name}
model_accuracy{model_name, period}
model_drift_score{model_name, drift_type}

# Training metrics
mlflow_model_training_duration_seconds{model_type, experiment_id}
mlflow_model_deployments_total{model_name, stage, status}
mlflow_active_models{service_name}
```

### Grafana Dashboards
- **Model Performance Overview** - Accuracy, latency, throughput
- **Training Pipeline Status** - Success rates, duration trends
- **Deployment Metrics** - Active models, deployment success rates
- **Drift Detection** - Data quality and distribution changes

### Alert Rules
```yaml
groups:
- name: mlops.rules
  rules:
  - alert: ModelAccuracyDrop
    expr: model_accuracy < 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Model {{ $labels.model_name }} accuracy dropped below threshold"

  - alert: ModelDriftDetected  
    expr: model_drift_score > 0.1
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Data drift detected in model {{ $labels.model_name }}"
```

## 🔍 Troubleshooting

### Common Issues

1. **MLflow Server Connection Issues**
   ```bash
   # Check database connection
   docker-compose logs mlflow-server
   
   # Verify PostgreSQL connectivity
   docker-compose exec postgres psql -U user -d mlflow -c "SELECT 1;"
   ```

2. **Artifact Storage Issues**
   ```bash
   # Check MinIO connectivity
   docker-compose logs minio
   
   # Verify bucket creation
   docker-compose exec minio mc ls local/selfmonitor-ml-artifacts
   ```

3. **Model Deployment Failures**
   ```bash
   # Check Kubernetes resources
   kubectl describe deployment fraud-detection-deployment
   
   # View pod logs
   kubectl logs -l app=fraud-detection
   ```

### Performance Optimization
- **Database Tuning**: Optimize PostgreSQL for MLflow workloads
- **Storage Performance**: Use high-performance storage for artifacts
- **Resource Allocation**: Right-size CPU/memory for training jobs
- **Caching Strategy**: Implement Redis caching for frequent queries

## 📋 Roadmap

### Q1 2024
- [x] Basic MLflow setup with experiment tracking
- [x] Automated training pipelines
- [x] Model deployment to Kubernetes
- [x] Performance monitoring and drift detection

### Q2 2024
- [ ] Advanced hyperparameter optimization (Optuna)
- [ ] Feature store integration (Feast)
- [ ] Multi-region model deployment
- [ ] Advanced A/B testing framework

### Q3 2024
- [ ] AutoML capabilities
- [ ] Model explainability integration (SHAP)
- [ ] Data lineage tracking
- [ ] Compliance and audit trails

### Q4 2024
- [ ] Edge deployment capabilities
- [ ] Real-time feature computation
- [ ] Advanced anomaly detection
- [ ] Multi-cloud support

---

## 📚 API Reference

### MLflow Server API
```bash
# Health check
GET /health

# List experiments  
GET /experiments

# List registered models
GET /models

# Promote model to staging
POST /models/{model_name}/promote/staging

# Get model performance
GET /models/{model_name}/performance
```

### Model Serving API
```bash
# Model prediction
POST /ml/{model_name}/predict
{
  "features": {"amount": 100.0, "merchant": "grocery_store"},
  "model_version": "latest"
}

# Batch prediction
POST /ml/{model_name}/batch_predict

# Model health
GET /ml/{model_name}/health
```

---

**Built with ❤️ for SelfMonitor FinTech Platform**

For more information, see:
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Kubernetes MLOps Best Practices](https://kubernetes.io/blog/2021/09/27/ml-platform/)
- [Model Monitoring Strategies](https://neptune.ai/blog/ml-model-monitoring-best-tools)