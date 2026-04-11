# Smoke-check HTTP endpoints after `docker compose up` (nginx on :8000).
# Usage: .\scripts\smoke_api_health.ps1 [-BaseUrl http://localhost:8000]

param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$paths = @(
    "/health",
    "/api/invoices/health",
    "/api/auth/health",
    "/api/transactions/health",
    "/api/documents/health",
    "/api/banking/health"
)

foreach ($p in $paths) {
    $url = "$BaseUrl$p"
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
        Write-Host "OK $($r.StatusCode) $url"
    } catch {
        Write-Warning "FAIL $url : $_"
    }
}
