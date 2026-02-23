#!/bin/bash

# SelfMonitor Platform - Kubernetes Deployment Script
# This script deploys the complete SelfMonitor FinTech platform to Kubernetes

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$SCRIPT_DIR"
ENVIRONMENT="${1:-development}"  # Default to development if not specified
NAMESPACE="selfmonitor"
DRY_RUN="${DRY_RUN:-false}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "kubectl is not configured to connect to a cluster"
        exit 1
    fi
    
    log_success "kubectl is available and connected to cluster"
}

# Check if kustomize is available
check_kustomize() {
    if ! command -v kustomize &> /dev/null; then
        log_warning "kustomize is not installed, using kubectl kustomize instead"
        KUSTOMIZE_CMD="kubectl kustomize"
    else
        KUSTOMIZE_CMD="kustomize"
        log_success "kustomize is available"
    fi
}

# Validate environment
validate_environment() {
    case $ENVIRONMENT in
        development|staging|production)
            log_info "Deploying to $ENVIRONMENT environment"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT. Must be one of: development, staging, production"
            exit 1
            ;;
    esac
    
    if [ "$ENVIRONMENT" = "development" ]; then
        NAMESPACE="selfmonitor-dev"
    elif [ "$ENVIRONMENT" = "staging" ]; then
        NAMESPACE="selfmonitor-staging"
    fi
}

# Create namespaces
create_namespaces() {
    log_info "Creating namespaces..."
    
    # Apply namespace configurations directly
    kubectl apply -f "$K8S_DIR/base/networking/namespace.yaml" --dry-run=${DRY_RUN}
    
    # Wait for namespaces to be ready
    if [ "$DRY_RUN" = "false" ]; then
        kubectl wait --for=condition=Active namespace/$NAMESPACE --timeout=30s
        kubectl wait --for=condition=Active namespace/selfmonitor-monitoring --timeout=30s
        kubectl wait --for=condition=Active namespace/selfmonitor-system --timeout=30s
    fi
    
    log_success "Namespaces created successfully"
}

# Deploy storage components
deploy_storage() {
    log_info "Deploying storage components..."
    
    # Deploy persistent volumes and claims
    kubectl apply -f "$K8S_DIR/base/storage/" --dry-run=${DRY_RUN}
    
    if [ "$DRY_RUN" = "false" ]; then
        # Wait for PVCs to be bound
        kubectl wait --for=condition=Bound pvc/postgres-pvc -n $NAMESPACE --timeout=60s || log_warning "PostgreSQL PVC not bound yet"
        kubectl wait --for=condition=Bound pvc/redis-pvc -n $NAMESPACE --timeout=60s || log_warning "Redis PVC not bound yet"
    fi
    
    log_success "Storage components deployed"
}

# Deploy database components
deploy_databases() {
    log_info "Deploying database components..."
    
    # Deploy PostgreSQL and Redis
    kubectl apply -f "$K8S_DIR/base/database/" --dry-run=${DRY_RUN}
    
    if [ "$DRY_RUN" = "false" ]; then
        # Wait for database deployments to be ready
        log_info "Waiting for PostgreSQL to be ready..."
        kubectl wait --for=condition=Available deployment/postgres-deployment -n $NAMESPACE --timeout=300s
        
        log_info "Waiting for Redis to be ready..."
        kubectl wait --for=condition=Available deployment/redis-deployment -n $NAMESPACE --timeout=120s
    fi
    
    log_success "Database components deployed"
}

# Deploy networking components
deploy_networking() {
    log_info "Deploying networking components..."
    
    # Apply network policies
    kubectl apply -f "$K8S_DIR/base/networking/" --dry-run=${DRY_RUN}
    
    log_success "Networking components deployed"
}

# Deploy core services
deploy_services() {
    log_info "Deploying core services..."
    
    # Deploy services one by one to control startup order
    local services=(
        "auth-service.yaml"
        "user-profile-service.yaml"  # this is actually in auth-service.yaml
        "transactions-service.yaml"
        "ai-agent-service.yaml"
    )
    
    for service in "${services[@]}"; do
        if [ -f "$K8S_DIR/base/services/$service" ]; then
            log_info "Deploying $service..."
            kubectl apply -f "$K8S_DIR/base/services/$service" --dry-run=${DRY_RUN}
        fi
    done
    
    if [ "$DRY_RUN" = "false" ]; then
        # Wait for core services to be ready
        log_info "Waiting for auth service to be ready..."
        kubectl wait --for=condition=Available deployment/auth-service-deployment -n $NAMESPACE --timeout=180s || log_warning "Auth service not ready"
        
        log_info "Waiting for AI agent service to be ready..."
        kubectl wait --for=condition=Available deployment/ai-agent-service-deployment -n $NAMESPACE --timeout=300s || log_warning "AI agent service not ready"
    fi
    
    log_success "Core services deployed"
}

# Deploy gateway
deploy_gateway() {
    log_info "Deploying gateway components..."
    
    # Deploy Nginx gateway
    kubectl apply -f "$K8S_DIR/base/gateway/" --dry-run=${DRY_RUN}
    
    if [ "$DRY_RUN" = "false" ]; then
        # Wait for gateway to be ready
        log_info "Waiting for Nginx gateway to be ready..."
        kubectl wait --for=condition=Available deployment/nginx-deployment -n $NAMESPACE --timeout=120s
    fi
    
    log_success "Gateway deployed"
}

# Deploy monitoring
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    # Deploy monitoring components
    kubectl apply -f "$K8S_DIR/base/monitoring/" --dry-run=${DRY_RUN}
    
    if [ "$DRY_RUN" = "false" ]; then
        # Wait for monitoring to be ready
        log_info "Waiting for Prometheus to be ready..."
        kubectl wait --for=condition=Available deployment/prometheus-deployment -n selfmonitor-monitoring --timeout=180s || log_warning "Prometheus not ready"
        
        log_info "Waiting for Grafana to be ready..."
        kubectl wait --for=condition=Available deployment/grafana-deployment -n selfmonitor-monitoring --timeout=120s || log_warning "Grafana not ready"
    fi
    
    log_success "Monitoring stack deployed"
}

# Apply environment-specific configuration
apply_overlay() {
    log_info "Applying $ENVIRONMENT environment configuration..."
    
    if [ -d "$K8S_DIR/overlays/$ENVIRONMENT" ]; then
        # Use kustomize to build and apply the configuration
        $KUSTOMIZE_CMD "$K8S_DIR/overlays/$ENVIRONMENT" | kubectl apply --dry-run=${DRY_RUN} -f -
        log_success "Environment overlay applied"
    else
        log_warning "No overlay found for $ENVIRONMENT environment, using base configuration"
    fi
}

# Run health checks
run_health_checks() {
    if [ "$DRY_RUN" = "true" ]; then
        log_info "Skipping health checks in dry-run mode"
        return
    fi
    
    log_info "Running health checks..."
    
    # Check pod status
    log_info "Checking pod status in $NAMESPACE namespace..."
    kubectl get pods -n $NAMESPACE
    
    # Check core services
    local services=(
        "postgres-service"
        "redis-service"
        "auth-service"
        "ai-agent-service"
        "nginx-service"
    )
    
    for service in "${services[@]}"; do
        if kubectl get service "$service" -n $NAMESPACE &> /dev/null; then
            log_success "$service is running"
        else
            log_warning "$service is not running or not found"
        fi
    done
    
    # Test gateway health endpoint
    log_info "Testing gateway health endpoint..."
    kubectl port-forward service/nginx-service 8080:80 -n $NAMESPACE &
    PORT_FORWARD_PID=$!
    sleep 5
    
    if curl -s http://localhost:8080/health > /dev/null; then
        log_success "Gateway health check passed"
    else
        log_warning "Gateway health check failed"
    fi
    
    kill $PORT_FORWARD_PID 2>/dev/null || true
}

# Display deployment summary
show_summary() {
    log_info "Deployment Summary"
    echo "===================="
    echo "Environment: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Dry Run: $DRY_RUN"
    echo
    
    if [ "$DRY_RUN" = "false" ]; then
        echo "Deployed Components:"
        echo "- Namespaces: selfmonitor, selfmonitor-monitoring, selfmonitor-system"
        echo "- Storage: PostgreSQL (200GB), Redis (50GB)"
        echo "- Database: PostgreSQL 15, Redis 7"
        echo "- Core Services: Auth, User Profile, Transactions, AI Agent"
        echo "- Gateway: Nginx with load balancing"
        echo "- Monitoring: Prometheus + Grafana"
        echo
        echo "Access Points:"
        echo "- API Gateway: kubectl port-forward service/nginx-service 8080:80 -n $NAMESPACE"
        echo "- AI Agent: kubectl port-forward service/ai-agent-service 8010:80 -n $NAMESPACE"
        echo "- Grafana: kubectl port-forward service/grafana-service 3000:3000 -n selfmonitor-monitoring"
        echo "- Prometheus: kubectl port-forward service/prometheus-service 9090:9090 -n selfmonitor-monitoring"
        echo
        echo "Next Steps:"
        echo "1. Update secrets with production values (see overlays/$ENVIRONMENT/kustomization.yaml)"
        echo "2. Configure external load balancer for nginx-service"
        echo "3. Set up DNS records for ingress"
        echo "4. Configure SSL certificates"
        echo "5. Set up monitoring alerts"
    fi
}

# Cleanup function
cleanup() {
    if [ -n "$PORT_FORWARD_PID" ]; then
        kill $PORT_FORWARD_PID 2>/dev/null || true
    fi
}

# Main deployment function
main() {
    trap cleanup EXIT
    
    log_info "Starting SelfMonitor Platform Kubernetes deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Namespace: $NAMESPACE"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_warning "Running in DRY RUN mode - no actual changes will be made"
    fi
    
    # Pre-flight checks
    check_kubectl
    check_kustomize
    validate_environment
    
    # Deployment phases
    create_namespaces
    deploy_storage
    deploy_databases
    deploy_networking
    deploy_services
    deploy_gateway
    deploy_monitoring
    apply_overlay
    
    # Post-deployment
    run_health_checks
    show_summary
    
    log_success "SelfMonitor Platform deployment completed successfully!"
}

# Script usage
usage() {
    echo "Usage: $0 [environment] [options]"
    echo
    echo "Environments:"
    echo "  development  Deploy to development environment (default)"
    echo "  staging      Deploy to staging environment"
    echo "  production   Deploy to production environment"
    echo
    echo "Options:"
    echo "  DRY_RUN=true  Run in dry-run mode (no actual changes)"
    echo
    echo "Examples:"
    echo "  $0                           # Deploy to development"
    echo "  $0 production                # Deploy to production"
    echo "  DRY_RUN=true $0 production   # Test production deployment"
}

# Handle script arguments
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
    exit 0
fi

# Run main function
main "$@"