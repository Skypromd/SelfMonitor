# SelfMonitor Platform - Kubernetes Infrastructure

Enterprise-grade Kubernetes deployment for SelfMonitor FinTech Platform with 23+ microservices, including the revolutionary SelfMate AI Agent.

## 🏗️ Architecture Overview

```
SelfMonitor Kubernetes Architecture
│
├── 🌐 Ingress & Load Balancing
│   ├── Nginx Gateway (3+ replicas)
│   ├── SSL Termination & Rate Limiting
│   └── Service Mesh Routing
│
├── 🤖 Core Services (20+ microservices)
│   ├── SelfMate AI Agent (GPT-4 powered)
│   ├── Authentication & Authorization
│   ├── Transaction Processing
│   ├── Real-time Analytics
│   ├── Banking Connectors
│   ├── Tax Engine
│   ├── Compliance & Audit
│   ├── Document Processing
│   └── Business Intelligence
│
├── 💾 Data Layer
│   ├── PostgreSQL Cluster (15 databases)
│   ├── Redis Cache & Sessions
│   ├── Weaviate Vector Database
│   └── Automated Backups
│
├── 📊 Monitoring & Observability
│   ├── Prometheus Metrics
│   ├── Grafana Dashboards
│   ├── Custom Alerting
│   └── Service Health Checks
│
└── 🛡️ Security & Compliance
    ├── Network Policies
    ├── Pod Security Standards
    ├── Secret Management
    └── RBAC Controls
```

## 🚀 Quick Start

### Prerequisites
- Kubernetes 1.24+ cluster
- kubectl configured
- 32+ GB RAM available
- 500+ GB storage
- Load balancer support

### 1. Deploy Development Environment
```bash
# Clone the repository
git clone <repository-url>
cd SelfMonitor/infra/k8s

# Make deployment script executable
chmod +x deploy.sh

# Deploy to development
./deploy.sh development
```

### 2. Deploy Production Environment
```bash
# First, update production secrets
vim overlays/production/kustomization.yaml

# Deploy to production
./deploy.sh production
```

### 3. Access the Platform
```bash
# API Gateway
kubectl port-forward service/nginx-service 8080:80 -n selfmonitor

# SelfMate AI Agent
kubectl port-forward service/ai-agent-service 8010:80 -n selfmonitor

# Grafana Dashboard
kubectl port-forward service/grafana-service 3000:3000 -n selfmonitor-monitoring
```

## 📁 Directory Structure

```
infra/k8s/
├── base/                          # Base Kubernetes resources
│   ├── database/                  # PostgreSQL & Redis configurations
│   ├── services/                  # Microservice deployments
│   ├── gateway/                   # Nginx & Ingress configurations
│   ├── storage/                   # Persistent volume configurations
│   ├── networking/                # Network policies & namespaces
│   ├── monitoring/                # Prometheus & Grafana
│   └── kustomization.yaml         # Base Kustomization
├── overlays/                      # Environment-specific configurations
│   ├── development/               # Development environment
│   ├── staging/                   # Staging environment
│   └── production/                # Production environment
├── deploy.sh                      # Automated deployment script
└── README.md                      # This file
```

## 🔧 Configuration Management

### Base Configuration (`base/`)
- **Namespace Management**: Multi-tenant isolation
- **Storage Classes**: Optimized for database workloads
- **Service Discovery**: Automatic service registration
- **Security Policies**: Pod security & network isolation
- **Resource Limits**: Optimized for cost and performance

### Environment Overlays (`overlays/`)

#### Development
- Single replica deployments
- Reduced resource allocation
- Debug logging enabled
- Development secrets
- Local storage options

#### Staging
- Production-like scaling
- Realistic data volumes
- Performance testing setup
- Staging-specific integrations

#### Production
- High-availability (3-5 replicas)
- Production resource allocation
- Security-hardened configuration
- External secret management
- Monitoring & alerting

## 🏢 Core Services

### 🤖 SelfMate AI Agent (`ai-agent-service`)
- **Purpose**: Autonomous financial advisor
- **Technology**: GPT-4, FastAPI, Redis + Weaviate
- **Scaling**: 2-10 replicas with HPA
- **Resources**: 2-8Gi RAM, 1-4 CPU cores
- **Special Features**: Session affinity, streaming support

### 🔐 Authentication Service (`auth-service`)
- **Purpose**: JWT-based authentication & authorization
- **Technology**: FastAPI, SQLite
- **Scaling**: 3-5 replicas
- **Resources**: 256Mi-1Gi RAM

### 👤 User Profile Service (`user-profile-service`)
- **Purpose**: User data management & preferences
- **Technology**: FastAPI, PostgreSQL
- **Scaling**: 2-3 replicas
- **Database**: `db_user_profile`

### 💰 Transactions Service (`transactions-service`)
- **Purpose**: Financial transaction processing
- **Technology**: FastAPI, PostgreSQL
- **Scaling**: 3-10 replicas with HPA
- **Database**: `db_transactions`

### 📊 Analytics Service (`analytics-service`)
- **Purpose**: Real-time financial analytics
- **Technology**: FastAPI, PostgreSQL, Redis
- **Scaling**: 2-8 replicas with HPA
- **Database**: `db_analytics`

## 💾 Data Architecture

### PostgreSQL Cluster
- **Version**: PostgreSQL 15.5
- **Databases**: 15 specialized databases
- **Storage**: 50-200Gi with automatic backups
- **Features**: Connection pooling, monitoring, replication

#### Database List:
- `db_auth` - Authentication data
- `db_user_profile` - User profiles & preferences
- `db_transactions` - Financial transactions
- `db_analytics` - Business intelligence data
- `db_compliance` - Audit & compliance logs
- `db_documents` - Document storage metadata
- `db_advice` - Financial advice history
- `db_ai_agent` - AI agent conversations & memory
- `db_business_intelligence` - BI reports & dashboards
- `db_fraud_detection` - Fraud analysis data
- `db_predictive_analytics` - ML model data
- `db_monitoring` - System monitoring data

### Redis Cluster
- **Version**: Redis 7.2
- **Purpose**: Caching, sessions, AI agent memory
- **Storage**: 10-50Gi persistent storage
- **Features**: AOF persistence, monitoring, clustering

### Weaviate Vector Database
- **Purpose**: AI agent semantic search & embeddings
- **Integration**: Embedded with AI agent service
- **Features**: Real-time vector search, conversation memory

## 🌐 Gateway & Networking

### Nginx Gateway
- **Replicas**: 3-5 instances
- **Features**: Load balancing, rate limiting, SSL termination
- **Routing**: Path-based routing to microservices
- **Security**: CORS, security headers, request filtering

### Ingress Configuration
- **Domains**: 
  - `api.selfmonitor.app` - Main API gateway
  - `ai.selfmonitor.app` - AI agent dedicated endpoint
  - `app.selfmonitor.app` - Web application
  - `grafana.selfmonitor.app` - Monitoring dashboard
- **SSL**: Automatic Let's Encrypt certificates
- **Rate Limiting**: Service-specific limits

### Service Mesh Routing
- **Auth Service**: `/auth/*`
- **User Profiles**: `/users/*`
- **Transactions**: `/transactions/*`
- **AI Agent**: `/ai/*` (with streaming support)
- **Analytics**: `/analytics/*`
- **Banking**: `/banking/*`
- **Tax Engine**: `/tax/*`

## 📊 Monitoring & Observability

### Prometheus Metrics
- **Collection**: 15-second intervals
- **Retention**: 30 days (50GB)
- **Targets**: All microservices, databases, infrastructure
- **Custom Metrics**: AI agent performance, business KPIs

### Grafana Dashboards
- **Platform Overview**: Service health, request rates, response times
- **AI Agent Monitoring**: Conversation analytics, model performance
- **Database Performance**: Query performance, connection pools
- **Business Intelligence**: Revenue metrics, user engagement

### Alerting Rules
- **Service Down**: Immediate critical alert
- **High Response Time**: >10 seconds for AI agent
- **High Error Rate**: >10% error rate
- **Resource Utilization**: >90% memory, >85% CPU
- **Database Issues**: Connection failures, slow queries

## 🛡️ Security & Compliance

### Network Security
- **Network Policies**: Deny-all default with explicit allow rules
- **Pod Security**: Non-root containers, read-only filesystems
- **Secret Management**: Kubernetes secrets with planned Vault integration
- **Service Mesh**: mTLS between services (planned)

### Compliance Features
- **Audit Logging**: All API calls logged
- **Data Encryption**: At-rest and in-transit
- **Access Control**: RBAC with minimal privilege
- **Backup Security**: Encrypted backups with rotation

## 🔄 Deployment Patterns

### Rolling Updates
- **Strategy**: RollingUpdate with MaxUnavailable=1
- **Health Checks**: Readiness/liveness probes
- **Zero Downtime**: Guaranteed for stateless services

### Scaling Strategies
- **Horizontal Pod Autoscaler (HPA)**: CPU/memory based
- **Custom Metrics**: Request rate and queue depth
- **Predictive Scaling**: Based on historical patterns

### Backup & Disaster Recovery
- **Database Backups**: Every 6 hours with 30-day retention
- **Configuration Backups**: GitOps with version control
- **Disaster Recovery**: Multi-AZ deployment support

## 📈 Performance Optimization

### Resource Allocation
- **Requests vs Limits**: 2:1 ratio for efficient packing
- **Node Affinity**: Database workloads on dedicated nodes
- **Pod Anti-Affinity**: Spread critical services across nodes

### Caching Strategy
- **Redis**: Application-level caching
- **CDN**: Static assets (planned)
- **Database**: Query result caching

## 🚦 Environment Management

### Development (`selfmonitor-dev`)
```bash
# Quick development deployment
./deploy.sh development

# Access services locally
kubectl port-forward service/nginx-service 8080:80 -n selfmonitor-dev
```

### Staging (`selfmonitor-staging`)
```bash
# Deploy to staging for testing
./deploy.sh staging

# Run integration tests
kubectl apply -f tests/integration/
```

### Production (`selfmonitor`)
```bash
# Production deployment with safeguards
DRY_RUN=true ./deploy.sh production  # Test first
./deploy.sh production               # Deploy
```

## 🔍 Troubleshooting

### Common Issues

#### Pod Startup Failures
```bash
# Check pod status
kubectl get pods -n selfmonitor

# View pod logs
kubectl logs <pod-name> -n selfmonitor

# Describe pod for events
kubectl describe pod <pod-name> -n selfmonitor
```

#### Database Connection Issues
```bash
# Check database status
kubectl get pods -l app=postgres -n selfmonitor

# Test database connectivity
kubectl exec -it <postgres-pod> -n selfmonitor -- psql -U selfmonitor -d selfmonitor_production
```

#### Service Discovery Problems
```bash
# Check service endpoints
kubectl get endpoints -n selfmonitor

# Test service connectivity
kubectl run test-pod --rm -it --image=busybox -- sh
# Inside pod: wget -qO- http://auth-service/health
```

### Debug Commands
```bash
# View all resources in namespace
kubectl get all -n selfmonitor

# Check resource usage
kubectl top pods -n selfmonitor
kubectl top nodes

# View events
kubectl get events -n selfmonitor --sort-by='.lastTimestamp'

# Check ingress status
kubectl describe ingress selfmonitor-ingress -n selfmonitor
```

## 🔄 Updates & Maintenance

### Rolling Updates
```bash
# Update single service
kubectl set image deployment/ai-agent-service-deployment ai-agent=selfmonitor/ai-agent-service:v1.1.0 -n selfmonitor

# Monitor rollout
kubectl rollout status deployment/ai-agent-service-deployment -n selfmonitor

# Rollback if needed
kubectl rollout undo deployment/ai-agent-service-deployment -n selfmonitor
```

### Backup Operations
```bash
# Manual database backup
kubectl exec postgres-deployment-<pod> -n selfmonitor -- pg_dump selfmonitor_production > backup.sql

# Restore from backup
kubectl exec -i postgres-deployment-<pod> -n selfmonitor -- psql selfmonitor_production < backup.sql
```

## 📞 Support & Documentation

### Internal Resources
- **Architecture Docs**: `docs/architecture/`
- **API Documentation**: OpenAPI specs in each service
- **Runbooks**: `docs/runbooks/`
- **Security Guidelines**: `docs/security/`

### External Resources
- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **Prometheus Monitoring**: https://prometheus.io/docs/
- **Grafana Dashboards**: https://grafana.com/docs/

### Team Contacts
- **DevOps Lead**: devops@selfmonitor.app
- **Platform Engineering**: platform@selfmonitor.app
- **On-Call Support**: oncall@selfmonitor.app

---

## 🎯 Next Steps

1. **Enhanced Security**: Implement Vault for secret management
2. **Service Mesh**: Deploy Istio for advanced traffic management
3. **Multi-Region**: Expand to multiple geographical regions
4. **Advanced Monitoring**: Implement distributed tracing with Jaeger
5. **Cost Optimization**: Implement cluster autoscaling and resource optimization

**SelfMonitor Kubernetes Platform** - Scaling Financial Intelligence to Millions of Users 🚀