# Запуск всех сервисов из docker-compose.yml + profile graphql (GraphQL gateway).
# Использование: .\scripts\run_full_stack.ps1   или   .\scripts\run_full_stack.ps1 -Build

param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path ".env")) {
    Write-Host "Copy .env.example to .env and edit secrets first." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example — edit it, then re-run." -ForegroundColor Yellow
    }
    exit 1
}

$args = @("compose", "--profile", "graphql", "up", "-d")
if ($Build) {
    $args = @("compose", "--profile", "graphql", "up", "--build", "-d")
}

Write-Host "docker $($args -join ' ')" -ForegroundColor Cyan
& docker @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nREST API: http://localhost:8000" -ForegroundColor Green
Write-Host "GraphQL:  http://localhost:4000/graphql" -ForegroundColor Green
Write-Host "`ndocker compose --profile graphql ps" -ForegroundColor Gray
