# Поднять v1 бэкенд для web-portal (nginx-gateway :8000). Требуется запущенный Docker Desktop.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Docker не отвечает. Запустите Docker Desktop и повторите." -ForegroundColor Red
  exit 1
}

& "$Root\scripts\compose_v1_up.ps1"

Write-Host "Ожидание :8000..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { $ok = $true; break }
  } catch { }
  Start-Sleep -Seconds 2
}
if ($ok) {
  Write-Host "Gateway OK: http://localhost:8000 — можно `npm run dev` в apps/web-portal" -ForegroundColor Green
} else {
  Write-Host "Health на :8000 не ответил за ~2 мин. Смотрите: docker compose logs nginx-gateway" -ForegroundColor Yellow
  exit 1
}
