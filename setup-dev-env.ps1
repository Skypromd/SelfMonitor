# SelfMonitor Development Environment Setup Script
# This script sets up the complete development environment for the SelfMonitor FinTech platform

param(
  [switch]$SkipDependencies,
  [switch]$SkipVirtualEnv,
  [switch]$SkipDocker,
  [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Setting up SelfMonitor Development Environment..." -ForegroundColor Green

# Function to write colored output
function Write-Step {
  param($Message)
  Write-Host "📝 $Message" -ForegroundColor Cyan
}

function Write-Success {
  param($Message)
  Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
  param($Message)
  Write-Host "⚠️ $Message" -ForegroundColor Yellow
}

function Write-Error {
  param($Message)
  Write-Host "❌ $Message" -ForegroundColor Red
}

# Check if running as Administrator
function Test-Administrator {
  $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

try {
  # 1. Check prerequisites
  Write-Step "Checking prerequisites..."
    
  # Check Python
  try {
    $pythonVersion = python --version 2>$null
    if ($pythonVersion -match "Python 3\.([8-9]|1[0-9])\.") {
      Write-Success "Python found: $pythonVersion"
    }
    else {
      Write-Error "Python 3.8+ required. Current: $pythonVersion"
      exit 1
    }
  }
  catch {
    Write-Error "Python not found. Please install Python 3.8+ from python.org"
    exit 1
  }
    
  # Check Node.js
  try {
    $nodeVersion = node --version 2>$null
    Write-Success "Node.js found: $nodeVersion"
  }
  catch {
    Write-Warning "Node.js not found. Install from nodejs.org for web portal development"
  }
    
  # Check Docker
  if (-not $SkipDocker) {
    try {
      $dockerVersion = docker --version 2>$null
      Write-Success "Docker found: $dockerVersion"
    }
    catch {
      Write-Warning "Docker not found. Install Docker Desktop for containerized services"
    }
  }
    
  # 2. Create Python virtual environment
  if (-not $SkipVirtualEnv) {
    Write-Step "Creating Python virtual environment..."
        
    if (Test-Path ".venv") {
      Write-Warning "Virtual environment already exists. Removing..."
      Remove-Item -Recurse -Force ".venv"
    }
        
    python -m venv .venv
    Write-Success "Virtual environment created"
        
    # Activate virtual environment
    Write-Step "Activating virtual environment..."
    & ".venv\Scripts\Activate.ps1"
        
    # Upgrade pip
    python -m pip install --upgrade pip
    Write-Success "Pip upgraded"
  }
    
  # 3. Install Python dependencies for all services
  if (-not $SkipDependencies) {
    Write-Step "Installing Python dependencies for all services..."
        
    $services = Get-ChildItem -Path "services" -Directory | Where-Object { 
      Test-Path (Join-Path $_.FullName "requirements.txt") 
    }
        
    foreach ($service in $services) {
      Write-Step "Installing dependencies for $($service.Name)..."
      try {
        Set-Location $service.FullName
        python -m pip install -r requirements.txt
        Write-Success "Dependencies installed for $($service.Name)"
      }
      catch {
        Write-Warning "Failed to install dependencies for $($service.Name): $_"
      }
      finally {
        Set-Location $PSScriptRoot
      }
    }
        
    # Install development tools
    Write-Step "Installing development tools..."
    python -m pip install black flake8 mypy pytest pytest-asyncio pytest-cov pytest-mock
    Write-Success "Development tools installed"
  }
    
  # 4. Install Node.js dependencies for web applications
  if (Get-Command "npm" -ErrorAction SilentlyContinue) {
    Write-Step "Installing Node.js dependencies..."
        
    # Web portal
    if (Test-Path "apps\web-portal\package.json") {
      Write-Step "Installing web portal dependencies..."
      Set-Location "apps\web-portal"
      npm install
      Set-Location $PSScriptRoot
      Write-Success "Web portal dependencies installed"
    }
        
    # GraphQL Gateway
    if (Test-Path "services\graphql-gateway\package.json") {
      Write-Step "Installing GraphQL gateway dependencies..."
      Set-Location "services\graphql-gateway"
      npm install
      Set-Location $PSScriptRoot
      Write-Success "GraphQL gateway dependencies installed"
    }
  }
    
  # 5. Create environment configuration
  Write-Step "Setting up environment configuration..."
    
  if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.development" ".env.local"
    Write-Success "Environment file created (.env.local)"
    Write-Warning "Please edit .env.local with your actual API keys and secrets"
  }
  else {
    Write-Success "Environment file already exists (.env.local)"
  }
    
  # 6. Set up database
  if (-not $SkipDocker) {
    Write-Step "Starting database containers..."
    try {
      docker-compose -f docker-compose.yml up -d postgres redis
      Write-Success "Database containers started"
    }
    catch {
      Write-Warning "Failed to start database containers. Run manually with: docker-compose up -d postgres redis"
    }
  }
    
  # 7. Run database migrations
  Write-Step "Running database migrations..."
  $migrationServices = @("user-profile-service", "transactions-service", "analytics-service")
    
  foreach ($service in $migrationServices) {
    if (Test-Path "services\${service}\alembic.ini") {
      Write-Step "Running migrations for $service..."
      try {
        Set-Location "services\${service}"
        alembic upgrade head
        Write-Success "Migrations completed for $service"
      }
      catch {
        Write-Warning "Failed to run migrations for ${service}: $($_.Exception.Message)"
      }
      finally {
        Set-Location $PSScriptRoot
      }
    }
  }
    
  # 8. Create development workspace file
  Write-Step "Creating VS Code workspace configuration..."
    
  $workspaceConfig = @{
    folders    = @(
      @{ path = "." }
      @{ path = "./services" }
      @{ path = "./apps" }
      @{ path = "./libs" }
      @{ path = "./ml" }
    )
    settings   = @{
      "python.defaultInterpreterPath"       = "./.venv/Scripts/python.exe"
      "python.terminal.activateEnvironment" = $true
    }
    extensions = @{
      recommendations = @(
        "ms-python.python"
        "ms-python.black-formatter" 
        "ms-azuretools.vscode-docker"
        "humao.rest-client"
      )
    }
  }
    
  $workspaceConfig | ConvertTo-Json -Depth 3 | Out-File "SelfMonitor.code-workspace" -Encoding UTF8
  Write-Success "VS Code workspace file created"
    
  # 9. Verify installation
  Write-Step "Verifying installation..."
    
  # Test Python import
  try {
    python -c "import fastapi, sqlalchemy, redis; print('Core dependencies OK')"
    Write-Success "Python dependencies verified"
  }
  catch {
    Write-Warning "Some Python dependencies may be missing"
  }
    
  # 10. Success summary
  Write-Host "`n🎉 Development environment setup complete!" -ForegroundColor Green
  Write-Host "
Next steps:
1. Edit .env.local with your API keys and secrets
2. Start the development services:
   - Run Task: 'Start All Services' (Ctrl+Shift+P)
   - Or manually: docker-compose up -d
3. Open SelfMonitor.code-workspace in VS Code
4. Start developing! 🚀

Quick start commands:
- Start specific service: F5 -> Select service to debug
- Run tests: Ctrl+Shift+P -> Tasks: Run Task -> Run Service Tests
- Format code: Ctrl+Shift+P -> Tasks: Run Task -> Format Python Code

Available services:
- User Profile: http://localhost:8001/docs
- Transactions: http://localhost:8002/docs  
- Auth Service: http://localhost:8003/docs
- GraphQL Gateway: http://localhost:4000/graphql
- Web Portal: http://localhost:3000

Happy coding! 💻
" -ForegroundColor Cyan

}
catch {
  Write-Error "Setup failed: $_"
  Write-Host "Run with -Verbose flag for more details" -ForegroundColor Yellow
  exit 1
}