# Istio Service Mesh Setup for SelfMonitor (PowerShell)
# Production-ready deployment script for Windows

param(
    [string]$Environment = "development"
)

$ErrorActionPreference = "Stop"
$IstioVersion = "1.19.0"

Write-Host "🕸️ Setting up Istio Service Mesh for SelfMonitor ($Environment)" -ForegroundColor Cyan

# Check if kubectl is available
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "❌ kubectl not found. Please install kubectl first." -ForegroundColor Red
    exit 1
}

# Check if istioctl is available
if (-not (Get-Command istioctl -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Installing Istio CLI..." -ForegroundColor Yellow
    
    # Download Istio
    $istioUrl = "https://github.com/istio/istio/releases/download/$IstioVersion/istio-$IstioVersion-win.zip"
    $istioZip = "istio-$IstioVersion-win.zip"
    
    Invoke-WebRequest -Uri $istioUrl -OutFile $istioZip
    Expand-Archive -Path $istioZip -DestinationPath . -Force
    
    # Add to PATH for this session
    $env:PATH += ";$PWD\istio-$IstioVersion\bin"
    
    Remove-Item $istioZip
}

$istioVersion = (istioctl version --client --short)
Write-Host "✓ Using Istio version: $istioVersion" -ForegroundColor Green

if ($Environment -eq "development") {
    Write-Host "🔧 Installing Istio for development..." -ForegroundColor Yellow
    
    # Install Istio with demo profile
    istioctl install --set values.defaultRevision=default -y
    
    # Enable automatic sidecar injection
    kubectl label namespace default istio-injection=enabled --overwrite
    
    Write-Host "✓ Istio installed with demo profile" -ForegroundColor Green
    
} elseif ($Environment -eq "production") {
    Write-Host "🚀 Installing Istio for production..." -ForegroundColor Yellow
    
    # Create namespace
    kubectl create namespace selfmonitor --dry-run=client -o yaml | kubectl apply -f -
    
    # Install Istio with custom configuration
    istioctl install -f infra/k8s/service-mesh/istio-operator.yaml -y
    
    # Apply security policies
    Write-Host "🛡️ Applying security policies..." -ForegroundColor Blue
    kubectl apply -f infra/k8s/service-mesh/security-policies.yaml
    
    # Apply traffic management
    Write-Host "🚦 Configuring traffic management..." -ForegroundColor Blue
    kubectl apply -f infra/k8s/service-mesh/traffic-management.yaml
    
    Write-Host "✓ Istio installed with production configuration" -ForegroundColor Green
}

# Verify installation
Write-Host "🔍 Verifying Istio installation..." -ForegroundColor Blue
kubectl get pods -n istio-system

# Wait for ingress gateway
Write-Host "⏳ Waiting for ingress gateway..." -ForegroundColor Yellow
kubectl rollout status deployment/istio-ingressgateway -n istio-system --timeout=300s

Write-Host ""
Write-Host "✅ Istio Service Mesh setup completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Access Service Mesh Dashboard:" -ForegroundColor Cyan
Write-Host "kubectl port-forward -n istio-system svc/kiali 20001:20001"
Write-Host "Dashboard: http://localhost:20001"
Write-Host ""

Write-Host "🎯 Features now available:" -ForegroundColor Yellow
Write-Host "• mTLS encryption between all services"
Write-Host "• Circuit breakers and retry policies"
Write-Host "• Canary deployments with traffic splitting"
Write-Host "• Distributed tracing integration"
Write-Host "• Advanced observability and metrics"
Write-Host ""

Write-Host "Next: Update service deployments with istio-injection labels" -ForegroundColor Cyan