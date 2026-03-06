$ErrorActionPreference = "SilentlyContinue"

# Stop existing processes on 8009 and 8010
Get-NetTCPConnection -State Listen -LocalPort 8009 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Get-NetTCPConnection -State Listen -LocalPort 8010 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Start-Sleep -Seconds 2

$venv = "B:\SelfMonitor\SelfMonitor\.venv\Scripts\uvicorn.exe"
$root = "B:\SelfMonitor\SelfMonitor"

# Start analytics-service (8009)
$p1 = Start-Process -FilePath $venv `
  -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8009" `
  -WorkingDirectory "$root\services\analytics-service" `
  -Environment @{
  AUTH_SECRET_KEY = "dev-local-secret-key-123"
  PYTHONPATH      = $root
  TEMP            = $env:TEMP
  TMP             = $env:TMP
} `
  -NoNewWindow -PassThru

# Start advice-service (8010)
$p2 = Start-Process -FilePath $venv `
  -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "8010" `
  -WorkingDirectory "$root\services\advice-service" `
  -Environment @{
  AUTH_SECRET_KEY = "dev-local-secret-key-123"
  PYTHONPATH      = $root
} `
  -NoNewWindow -PassThru

Write-Output "Started analytics PID $($p1.Id), advice PID $($p2.Id)"
Start-Sleep -Seconds 4

# Health check
$python = "$root\.venv\Scripts\python.exe"
& $python -c @"
import urllib.request
for port, path in [(8009, '/health'), (8010, '/health')]:
    try:
        r = urllib.request.urlopen(f'http://localhost:{port}{path}', timeout=5)
        print(f':{port} OK {r.status}')
    except Exception as e:
        print(f':{port} ERROR {e}')
"@
