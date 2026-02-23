#!/bin/bash
# Istio Service Mesh Setup for SelfMonitor
# Production-ready deployment script

set -e

ISTIO_VERSION="1.19.0"
ENVIRONMENT=${1:-development}

echo "🕸️ Setting up Istio Service Mesh for SelfMonitor ($ENVIRONMENT)"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if istioctl is available, install if needed
if ! command -v istioctl &> /dev/null; then
    echo "📦 Installing Istio CLI..."
    curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -
    export PATH="$PWD/istio-${ISTIO_VERSION}/bin:$PATH"
fi

echo "✓ Using Istio version: $(istioctl version --client --short)"

if [ "$ENVIRONMENT" = "development" ]; then
    echo "🔧 Installing Istio for development..."
    
    # Install Istio with demo profile (includes ingress gateway)
    istioctl install --set values.defaultRevision=default -y
    
    # Enable automatic sidecar injection for default namespace
    kubectl label namespace default istio-injection=enabled --overwrite
    
    echo "✓ Istio installed with demo profile"
    
elif [ "$ENVIRONMENT" = "production" ]; then
    echo "🚀 Installing Istio for production..."
    
    # Create selfmonitor namespace
    kubectl create namespace selfmonitor --dry-run=client -o yaml | kubectl apply -f -
    
    # Install Istio with custom operator configuration
    istioctl install -f infra/k8s/service-mesh/istio-operator.yaml -y
    
    # Apply security policies
    echo "🛡️ Applying security policies..."
    kubectl apply -f infra/k8s/service-mesh/security-policies.yaml
    
    # Apply traffic management rules
    echo "🚦 Configuring traffic management..."
    kubectl apply -f infra/k8s/service-mesh/traffic-management.yaml
    
    echo "✓ Istio installed with production configuration"
    
fi

# Verify installation
echo "🔍 Verifying Istio installation..."
kubectl get pods -n istio-system

# Check if ingress gateway is ready
echo "⏳ Waiting for ingress gateway..."
kubectl rollout status deployment/istio-ingressgateway -n istio-system --timeout=300s

# Get ingress gateway external IP
EXTERNAL_IP=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$EXTERNAL_IP" ]; then
    EXTERNAL_IP=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
fi

echo ""
echo "✅ Istio Service Mesh setup completed!"
echo ""
echo "📊 Service Mesh Dashboard:"
echo "kubectl port-forward -n istio-system svc/kiali 20001:20001"
echo "Access: http://localhost:20001"
echo ""

if [ "$ENVIRONMENT" = "production" ]; then
    echo "🌐 External Gateway IP: $EXTERNAL_IP"
    echo ""
fi

echo "🔧 Next steps:"
echo "1. Deploy services to namespace with istio-injection=enabled"
echo "2. Configure TLS certificates for external gateway"
echo "3. Set up monitoring with Prometheus/Grafana"
echo ""

echo "Example service update for sidecar injection:"
echo "kubectl patch deployment predictive-analytics -p '{\"spec\":{\"template\":{\"metadata\":{\"labels\":{\"version\":\"v1\"}}}}}'"
echo ""

echo "🎯 Istio features now available:"
echo "• mTLS encryption between all services"
echo "• Circuit breakers and retry policies"
echo "• Canary deployments with traffic splitting"
echo "• Distributed tracing integration"
echo "• Advanced observability and metrics"