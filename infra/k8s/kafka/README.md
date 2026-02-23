# SelfMonitor Kafka Deployment

Production-ready Apache Kafka deployment for SelfMonitor platform with full Confluent Platform integration.

## Overview

This deployment provides a complete event streaming infrastructure for SelfMonitor's 23+ microservices:

- **Apache Kafka 7.4.0** - High-throughput distributed streaming platform
- **Apache Zookeeper** - Distributed coordination service for Kafka
- **Confluent Schema Registry** - Schema management and evolution
- **Kafka Connect** - Scalable and reliable data integration
- **KSQLDB** - Stream processing database
- **Kafka UI** - Web-based management interface
- **Monitoring Stack** - Prometheus metrics and Grafana dashboards

## Architecture

### Event Streaming Topics

| Topic | Partitions | Retention | Use Case |
|-------|------------|-----------|----------|
| `user.events` | 12 | 7 days | User registration, login, profile updates |
| `transaction.events` | 12 | 30 days | Payment processing, transfers, balances |
| `fraud.alerts` | 8 | 90 days | Real-time fraud detection and alerts |
| `ml.predictions` | 8 | 7 days | AI model predictions and recommendations |
| `analytics.events` | 12 | 30 days | Business metrics and KPI tracking |
| `audit.events` | 6 | 1 year | Compliance and audit logging |
| `notification.events` | 6 | 7 days | Email, SMS, push notifications |
| `document.events` | 6 | 30 days | Document processing and OCR |
| `compliance.events` | 4 | 1 year | Regulatory compliance events |
| `integration.events` | 8 | 7 days | Third-party integration events |
| `system.events` | 4 | 30 days | Infrastructure and system events |

### Performance Specifications

- **Throughput**: 1M+ events per day
- **Latency**: < 10ms p99
- **Availability**: 99.9% SLA
- **Durability**: 3x replication factor
- **Retention**: Configurable per topic (7 days to 1 year)

## Quick Start

### Prerequisites

- Kubernetes cluster v1.25+
- Helm v3.8+
- Storage class with fast SSDs
- 8 CPU cores, 16GB RAM minimum per node

### Installation Options

#### Option 1: Direct Kubernetes Deployment

```bash
# Create namespace
kubectl apply -f infra/k8s/kafka/kafka-cluster.yaml

# Deploy Confluent Platform
kubectl apply -f infra/k8s/kafka/confluent-platform.yaml

# Deploy monitoring stack
kubectl apply -f infra/k8s/kafka/kafka-monitoring.yaml

# Check deployment status
kubectl get pods -n kafka
```

#### Option 2: Helm Chart Deployment

```bash
# Add Helm repository (if using external charts)
helm repo add selfmonitor https://charts.selfmonitor.com
helm repo update

# Install with default values
helm install kafka-cluster infra/k8s/kafka/helm/ \
  --namespace kafka \
  --create-namespace

# Install with custom values
helm install kafka-cluster infra/k8s/kafka/helm/ \
  --namespace kafka \
  --create-namespace \
  --values production-values.yaml
```

#### Option 3: Development Setup

```bash
# Start local Kafka with Docker Compose
cd infra/kafka
docker-compose -f docker-compose-kafka.yml up -d

# Create topics
python setup-kafka.py

# Verify installation
python -c "from topics_architecture import *; print('Topics created successfully')"
```

### Environment-Specific Configurations

#### Production
```bash
helm install kafka-cluster ./helm/ \
  --namespace kafka \
  --set environment=production \
  --set kafka.replicaCount=5 \
  --set kafka.resources.requests.memory=2Gi \
  --set kafka.persistence.size=100Gi \
  --set monitoring.enabled=true \
  --set security.enabled=true
```

#### Staging
```bash
helm install kafka-cluster ./helm/ \
  --namespace kafka \
  --set environment=staging \
  --set kafka.replicaCount=3 \
  --set kafka.resources.requests.memory=1Gi \
  --set kafka.persistence.size=50Gi \
  --set monitoring.enabled=true
```

#### Development
```bash
helm install kafka-cluster ./helm/ \
  --namespace kafka \
  --set environment=development \
  --set kafka.replicaCount=1 \
  --set zookeeper.replicaCount=1 \
  --set kafka.resources.requests.memory=512Mi \
  --set kafka.persistence.size=10Gi
```

## Service Integration

### Event Streaming Library

All SelfMonitor services use the centralized event streaming library:

```python
from libs.event_streaming.kafka_integration import EventStreamingMixin

class UserService(FastAPI, EventStreamingMixin):
    def __init__(self):
        super().__init__()
        self.init_event_streaming()
    
    async def create_user(self, user_data: dict):
        # Business logic
        user = await self.user_repository.create(user_data)
        
        # Emit event
        await self.emit_event(
            topic="user.events",
            event_type="user_created",
            data=user.dict(),
            user_id=user.id
        )
        
        return user
```

### Event Schemas (Avro)

Events use Avro schemas for serialization:

```python
USER_EVENT_SCHEMA = {
    "type": "record", 
    "name": "UserEvent",
    "fields": [
        {"name": "event_id", "type": "string"},
        {"name": "event_type", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "timestamp", "type": "long"},
        {"name": "data", "type": "string"}
    ]
}
```

### Consumer Groups

Each service has dedicated consumer groups:

```python
CONSUMER_GROUPS = {
    "analytics-service": ["user.events", "transaction.events", "analytics.events"],
    "fraud-detection": ["transaction.events", "user.events"],
    "notification-service": ["user.events", "notification.events"],
    "audit-service": ["audit.events", "compliance.events"],
    "ml-service": ["user.events", "transaction.events", "ml.predictions"]
}
```

## Monitoring and Alerting

### Access Kafka UI

```bash
# Port forward to access UI
kubectl port-forward -n kafka svc/kafka-ui-service 8080:8080

# Open browser
open http://localhost:8080
```

### Prometheus Metrics

Key metrics monitored:

- `kafka_brokers` - Number of active brokers
- `kafka_topic_partitions` - Partition count per topic  
- `kafka_consumer_lag` - Consumer lag per group
- `kafka_messages_per_sec` - Message throughput
- `kafka_bytes_per_sec` - Network throughput
- `kafka_log_size` - Log size on disk

### Grafana Dashboards

Pre-configured dashboards available:

1. **Kafka Overview** - Cluster health, throughput, topics
2. **Consumer Monitoring** - Lag, throughput, group status
3. **Broker Performance** - CPU, memory, disk, network
4. **Topic Analysis** - Message rates, retention, partition distribution

### Alerting Rules

Critical alerts configured:

- Broker down (1 minute)
- High consumer lag (> 1000 messages, 5 minutes)
- Disk usage > 80% (10 minutes)
- Under-replicated partitions (5 minutes)
- Offline partitions (1 minute)

## Operations

### Scaling

#### Scale Kafka Brokers
```bash
# Scale up brokers
kubectl scale statefulset kafka -n kafka --replicas=5

# Scale consumer applications
kubectl scale deployment analytics-service -n selfmonitor --replicas=3
```

#### Add Partitions to Topics
```bash
# Connect to Kafka pod
kubectl exec -it kafka-0 -n kafka -- bash

# Add partitions (can only increase)
kafka-topics --bootstrap-server localhost:9092 \
  --alter --topic user.events --partitions 24
```

### Topic Management

#### List Topics
```bash
kubectl exec kafka-0 -n kafka -- kafka-topics \
  --bootstrap-server localhost:9092 --list
```

#### Describe Topic
```bash
kubectl exec kafka-0 -n kafka -- kafka-topics \
  --bootstrap-server localhost:9092 --describe --topic user.events
```

#### Delete Topic
```bash
kubectl exec kafka-0 -n kafka -- kafka-topics \
  --bootstrap-server localhost:9092 --delete --topic temp.topic
```

### Consumer Group Management

#### List Consumer Groups
```bash
kubectl exec kafka-0 -n kafka -- kafka-consumer-groups \
  --bootstrap-server localhost:9092 --list
```

#### Describe Consumer Group
```bash
kubectl exec kafka-0 -n kafka -- kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group analytics-service
```

#### Reset Consumer Offset
```bash
kubectl exec kafka-0 -n kafka -- kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --reset-offsets --group analytics-service \
  --topic user.events --to-earliest --execute
```

### Backup and Recovery

#### Export Topic Data
```bash
# Create connector for backup
curl -X POST http://kafka-connect-service:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backup-user-events",
    "config": {
      "connector.class": "io.confluent.connect.s3.S3SinkConnector",
      "tasks.max": "3",
      "topics": "user.events",
      "s3.bucket.name": "kafka-backups",
      "storage.class": "io.confluent.connect.s3.storage.S3Storage",
      "format.class": "io.confluent.connect.s3.format.avro.AvroFormat",
      "partition.duration.ms": "86400000"
    }
  }'
```

#### Disaster Recovery
```bash
# Restore from backup
python infra/kafka/disaster-recovery.py \
  --source s3://kafka-backups/user.events \
  --target user.events.restored \
  --date 2024-01-01
```

## Security

### RBAC Configuration

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kafka-user
  namespace: selfmonitor
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kafka-client
  namespace: kafka
rules:
- apiGroups: [""]
  resources: ["services", "endpoints"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding  
metadata:
  name: kafka-user-binding
  namespace: kafka
subjects:
- kind: ServiceAccount
  name: kafka-user
  namespace: selfmonitor
roleRef:
  kind: Role
  name: kafka-client
  apiGroup: rbac.authorization.k8s.io
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: kafka-client-access
  namespace: kafka
spec:
  podSelector:
    matchLabels:
      app: kafka
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: selfmonitor
    ports:
    - protocol: TCP
      port: 9092
```

### SASL/SCRAM Authentication

```bash
# Create SCRAM credentials
kubectl exec kafka-0 -n kafka -- kafka-configs \
  --bootstrap-server localhost:9092 \
  --alter --add-config 'SCRAM-SHA-512=[password=secret123]' \
  --entity-type users --entity-name kafka-user
```

## Troubleshooting

### Common Issues

#### Broker Not Starting
```bash
# Check pod logs
kubectl logs kafka-0 -n kafka

# Check disk space
kubectl exec kafka-0 -n kafka -- df -h

# Check Zookeeper connectivity
kubectl exec kafka-0 -n kafka -- \
  kafka-broker-api-versions --bootstrap-server zookeeper-service:2181
```

#### High Consumer Lag
```bash
# Check consumer group status
kubectl exec kafka-0 -n kafka -- kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group analytics-service

# Scale up consumers
kubectl scale deployment analytics-service -n selfmonitor --replicas=5

# Monitor lag reduction
while true; do
  kubectl exec kafka-0 -n kafka -- kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --describe --group analytics-service | grep LAG
  sleep 10
done
```

#### Schema Registry Issues
```bash
# Check schema registry health
kubectl exec -n kafka deployment/schema-registry -- \
  curl -s http://localhost:8081/subjects

# List schemas
curl -s http://schema-registry-service.kafka:8081/subjects

# Register new schema
curl -X POST http://schema-registry-service.kafka:8081/subjects/user.events-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "..."}'
```

### Performance Tuning

#### Broker Configuration
```bash
# Increase heap size for brokers
kubectl patch statefulset kafka -n kafka -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "kafka",
          "env": [{
            "name": "KAFKA_HEAP_OPTS",
            "value": "-Xmx4G -Xms4G"
          }]
        }]
      }
    }
  }
}'
```

#### Enable Compression
```bash
# Enable compression for producers
export KAFKA_COMPRESSION_TYPE=snappy

# Update broker compression settings
kubectl exec kafka-0 -n kafka -- kafka-configs \
  --bootstrap-server localhost:9092 \
  --alter --add-config 'compression.type=snappy' \
  --entity-type topics --entity-name user.events
```

## Support

### Health Checks

```bash
# Overall cluster health
kubectl get pods -n kafka
kubectl get pvc -n kafka

# Kafka cluster health
kubectl exec kafka-0 -n kafka -- kafka-topics \
  --bootstrap-server localhost:9092 --list

# Schema registry health  
curl -f http://schema-registry-service.kafka:8081/subjects

# Kafka Connect health
curl -f http://kafka-connect-service.kafka:8083/connectors
```

### Log Analysis

```bash
# Kafka broker logs
kubectl logs kafka-0 -n kafka --tail=100

# Schema registry logs
kubectl logs deployment/schema-registry -n kafka --tail=100

# Kafka Connect logs
kubectl logs deployment/kafka-connect -n kafka --tail=100

# Consumer application logs
kubectl logs deployment/analytics-service -n selfmonitor --tail=100
```

### Contact Information

- **Team**: SelfMonitor DevOps
- **Email**: devops@selfmonitor.com  
- **Slack**: #kafka-support
- **Runbook**: [docs/runbooks/kafka-operations.md](../../../docs/runbooks/kafka-operations.md)
- **Escalation**: On-call rotation via PagerDuty