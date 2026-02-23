#!/bin/bash
# OpenTelemetry Tracing Setup for SelfMonitor
# Usage: ./setup-tracing.sh [development|production]

set -e

ENVIRONMENT=${1:-development}

echo "🔧 Setting up OpenTelemetry tracing for SelfMonitor ($ENVIRONMENT)"

if [ "$ENVIRONMENT" = "development" ]; then
    echo "📦 Starting Jaeger for local development..."
    
    # Start Jaeger with docker-compose
    docker-compose -f docker-compose.yml -f observability/docker-compose-tracing.yml up -d jaeger
    
    # Wait for Jaeger to be ready
    echo "⏳ Waiting for Jaeger to start..."
    sleep 10
    
    # Verify Jaeger is running
    if curl -f http://localhost:16686 > /dev/null 2>&1; then
        echo "✅ Jaeger UI available at: http://localhost:16686"
    else
        echo "❌ Jaeger failed to start properly"
        exit 1
    fi
    
elif [ "$ENVIRONMENT" = "production" ]; then
    echo "🚀 Deploying Jaeger to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace selfmonitor --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy Jaeger
    kubectl apply -f infra/k8s/observability/jaeger.yaml
    
    # Wait for deployment
    kubectl rollout status deployment/jaeger -n selfmonitor --timeout=300s
    
    echo "✅ Jaeger deployed to Kubernetes cluster"
    echo "🌐 Access via: kubectl port-forward svc/jaeger-service -n selfmonitor 16686:16686"
    
fi

echo "🎯 Installing OpenTelemetry dependencies in services..."

# Update predictive-analytics service (our pilot service)
(cd services/predictive-analytics && pip install -r requirements.txt)

echo ""
echo "🚀 OpenTelemetry setup completed!"
echo ""
echo "Next steps:"
echo "1. Restart predictive-analytics service"
echo "2. Make some API calls to generate traces"
echo "3. View traces in Jaeger UI"
echo ""
echo "Example test command:"
echo "curl -H 'Authorization: Bearer your-token' http://localhost:8000/api/predictions/recommendations/test-user"