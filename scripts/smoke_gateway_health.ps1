# Smoke health checks through nginx gateway (default http://localhost:8000).
$ErrorActionPreference = "Stop"
$Base = if ($env:GATEWAY_URL) { $env:GATEWAY_URL } else { "http://localhost:8000" }
$paths = @(
 "/api/auth/health",
    "/api/billing/health",
    "/api/transactions/health",
    "/api/documents/health",
    "/api/integrations/health",
    "/api/invoices/health",
    "/api/banking/health",
    "/api/tax/health"
)
foreach ($p in $paths) {
    $url = "$Base$p"
    Write-Host "GET $url"
    Invoke-WebRequest -Uri $url -UseBasicParsing | Out-Null
}
Write-Host "All gateway health checks passed."
