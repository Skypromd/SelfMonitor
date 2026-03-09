# SelfMonitor - Start all services
# Usage: powershell -ExecutionPolicy Bypass -File start-services.ps1

$ROOT = "B:\SelfMonitor\SelfMonitor"
$VENV = "$ROOT\.venv\Scripts\uvicorn.exe"

$commonEnv = @{
  AUTH_SECRET_KEY = "dev-local-secret-key-123"
  PYTHONPATH      = $ROOT
  TEMP            = $env:TEMP
  TMP             = $env:TMP
  PATH            = $env:PATH
}

Write-Host "Stopping existing services..." -ForegroundColor Yellow
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
Where-Object { $_.LocalPort -in 3000, 3001, 8001, 8005, 8006, 8009, 8010, 8012, 8015 } |
ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Stop-Process -Name node -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "All stopped." -ForegroundColor Gray

# --- auth-service :8001 ---
$env1 = $commonEnv.Clone()
$env1["AUTH_DB_PATH"] = "$ROOT\services\auth-service\auth.db"
$env1["AUTH_BOOTSTRAP_ADMIN"] = "true"
$env1["AUTH_ADMIN_EMAIL"] = "skypromd@gmail.com"
$env1["AUTH_ADMIN_PASSWORD"] = "VeryStrongPassword123!"
$env1["AUTH_REQUIRE_ADMIN_2FA"] = "false"
$p1 = Start-Process -FilePath $VENV -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8001" `
  -WorkingDirectory "$ROOT\services\auth-service" -PassThru -NoNewWindow `
  -RedirectStandardOutput "$ROOT\logs\auth_out.txt" -RedirectStandardError "$ROOT\logs\auth_err.txt" `
  -Environment $env1
Write-Host "auth-service       :8001  PID=$($p1.Id)" -ForegroundColor Cyan

# --- localization-service :8012 ---
$p2 = Start-Process -FilePath $VENV -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8012" `
  -WorkingDirectory "$ROOT\services\localization-service" -PassThru -NoNewWindow `
  -RedirectStandardOutput "$ROOT\logs\localization_out.txt" -RedirectStandardError "$ROOT\logs\localization_err.txt" `
  -Environment $commonEnv
Write-Host "localization-service :8012 PID=$($p2.Id)" -ForegroundColor Cyan

# --- user-profile-service :8005 ---
$env3 = $commonEnv.Clone()
$env3["DATABASE_URL"] = "sqlite+aiosqlite:///$ROOT/services/user-profile-service/profile.db"
$p3 = Start-Process -FilePath $VENV -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8005" `
  -WorkingDirectory "$ROOT\services\user-profile-service" -PassThru -NoNewWindow `
  -RedirectStandardOutput "$ROOT\logs\profile_out.txt" -RedirectStandardError "$ROOT\logs\profile_err.txt" `
  -Environment $env3
Write-Host "user-profile-service :8005 PID=$($p3.Id)" -ForegroundColor Cyan

# --- analytics-service :8009 ---
$p4 = Start-Process -FilePath $VENV -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8009" `
  -WorkingDirectory "$ROOT\services\analytics-service" -PassThru -NoNewWindow `
  -RedirectStandardOutput "$ROOT\logs\analytics_out.txt" -RedirectStandardError "$ROOT\logs\analytics_err.txt" `
  -Environment $commonEnv
Write-Host "analytics-service  :8009  PID=$($p4.Id)" -ForegroundColor Cyan

# --- advice-service :8010 ---
$p5 = Start-Process -FilePath $VENV -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8010" `
  -WorkingDirectory "$ROOT\services\advice-service" -PassThru -NoNewWindow `
  -RedirectStandardOutput "$ROOT\logs\advice_out.txt" -RedirectStandardError "$ROOT\logs\advice_err.txt" `
  -Environment $commonEnv
Write-Host "advice-service     :8010  PID=$($p5.Id)" -ForegroundColor Cyan

# --- documents-service :8006 ---
$env6 = $commonEnv.Clone()
$env6["DATABASE_URL"] = "sqlite+aiosqlite:///$ROOT/services/documents-service/documents.db"
$env6["CELERY_BROKER_URL"] = "memory://"
$env6["CELERY_RESULT_BACKEND"] = "cache+memory://"
$env6["AWS_ENDPOINT_URL"] = "http://localhost:9000"
$p6 = Start-Process -FilePath $VENV -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8006" `
  -WorkingDirectory "$ROOT\services\documents-service" -PassThru -NoNewWindow `
  -RedirectStandardOutput "$ROOT\logs\documents_out.txt" -RedirectStandardError "$ROOT\logs\documents_err.txt" `
  -Environment $env6
Write-Host "documents-service  :8006  PID=$($p6.Id)" -ForegroundColor Cyan

# --- banking-connector :8015 ---
$envBanking = $commonEnv.Clone()
$envBanking["VAULT_ADDR"]        = "http://localhost:8200"
$envBanking["VAULT_TOKEN"]       = "dev-root-token"
$envBanking["CELERY_BROKER_URL"] = "memory://"
$envBanking["PYTHONUTF8"]        = "1"
$pBanking = Start-Process -FilePath $VENV -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8015" `
  -WorkingDirectory "$ROOT\services\banking-connector" -PassThru -NoNewWindow `
  -RedirectStandardOutput "$ROOT\logs\banking_out.txt" -RedirectStandardError "$ROOT\logs\banking_err.txt" `
  -Environment $envBanking
Write-Host "banking-connector  :8015  PID=$($pBanking.Id)" -ForegroundColor Cyan
$nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source
if ($nodeExe) {
  Remove-Item "$ROOT\apps\web-portal\.next\dev\lock" -Force -ErrorAction SilentlyContinue
  $p7 = Start-Process -FilePath $nodeExe `
    -ArgumentList "$ROOT\apps\web-portal\node_modules\next\dist\bin\next", "dev" `
    -WorkingDirectory "$ROOT\apps\web-portal" -PassThru -NoNewWindow `
    -RedirectStandardOutput "$ROOT\logs\portal_out.txt" -RedirectStandardError "$ROOT\logs\portal_err.txt" `
    -Environment $commonEnv
  Write-Host "web-portal         :3000  PID=$($p7.Id)" -ForegroundColor Cyan
}
else {
  Write-Host "node not found in PATH - skipping web-portal" -ForegroundColor Red
}

# --- proxy-gateway :8000 ---
$gatewayPy = "$ROOT\proxy_gateway.py"
if (Test-Path $gatewayPy) {
  # Kill any existing process on port 8000
  Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Milliseconds 500
  $pGW = Start-Process -FilePath "$ROOT\.venv\Scripts\python.exe" -ArgumentList $gatewayPy `
    -WorkingDirectory $ROOT -PassThru -NoNewWindow `
    -RedirectStandardOutput "$ROOT\logs\gateway_out.txt" -RedirectStandardError "$ROOT\logs\gateway_err.txt"
  Write-Host "proxy-gateway      :8000  PID=$($pGW.Id)" -ForegroundColor Cyan
}
else {
  Write-Host "proxy_gateway.py not found - skipping gateway" -ForegroundColor Red
}

Write-Host ""
Write-Host "Waiting 25 seconds for services to start (Next.js needs ~20s to compile)..." -ForegroundColor Yellow
Start-Sleep -Seconds 25

# Health check
# Detect actual portal port (Next.js may fall back to 3001 if 3000 is briefly busy)
$portalPort = 3000
try { $null = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop }
catch { if ((Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue)) { $portalPort = 3001 } }

# Portal health check with retry (first compile takes up to 15s after Ready)
$portalOk = $false
for ($i = 0; $i -lt 6; $i++) {
  try {
    $null = Invoke-WebRequest -Uri "http://localhost:$portalPort" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    $portalOk = $true; break
  }
  catch { Start-Sleep -Seconds 5 }
}

$checks = @(
  @{name = "portal    :$portalPort"; url = "http://localhost:$portalPort"; skip = $true; ok = $portalOk },
  @{name = "gateway   :8080"; url = "http://localhost:8080/health" },
  @{name = "auth      :8001"; url = "http://localhost:8001/health" },
  @{name = "profile   :8005"; url = "http://localhost:8005/health" },
  @{name = "documents :8006"; url = "http://localhost:8006/health" },
  @{name = "analytics :8009"; url = "http://localhost:8009/health" },
  @{name = "advice    :8010"; url = "http://localhost:8010/health" },
  @{name = "localize  :8012"; url = "http://localhost:8012/docs" },
  @{name = "banking   :8015"; url = "http://localhost:8015/health" }
)
Write-Host ""
Write-Host "Health check:" -ForegroundColor Yellow
foreach ($c in $checks) {
  if ($c.skip) {
    if ($c.ok) { Write-Host "  $($c.name)  OK 200" -ForegroundColor Green }
    else { Write-Host "  $($c.name)  FAIL" -ForegroundColor Red }
    continue
  }
  try {
    $r = Invoke-WebRequest -Uri $c.url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  $($c.name)  OK $($r.StatusCode)" -ForegroundColor Green
  }
  catch {
    Write-Host "  $($c.name)  FAIL" -ForegroundColor Red
  }
}
Write-Host ""
Write-Host "Logs are in: $ROOT\logs\" -ForegroundColor Gray
Write-Host "Portal: http://localhost:$portalPort  |  Login: skypromd@gmail.com / VeryStrongPassword123!" -ForegroundColor White
