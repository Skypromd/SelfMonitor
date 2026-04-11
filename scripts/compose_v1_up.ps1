# Поднять только контур v1 MVP (см. docs/production-scope.md).
# Требуется Docker Compose v2 и файл .env (скопируйте из .env.example).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$composeFiles = @("-f", "docker-compose.yml")
if ($env:USE_COMPOSE_PROD -eq "1") {
  $composeFiles += "-f", "docker-compose.prod.yml"
  if (Test-Path ".env.prod") {
    $composeFiles += "--env-file", ".env.prod"
  }
}

$services = @(
  "postgres-master",
  "redis-master",
  "redis",
  "minio",
  "vault",
  "categorization-service",
  "compliance-service",
  "consent-service",
  "auth-service",
  "user-profile-service",
  "transactions-service",
  "banking-connector",
  "documents-service",
  "celery-worker-docs",
  "weaviate",
  "qna-service",
  "integrations-service",
  "calendar-service",
  "tax-engine",
  "mtd-agent",
  "invoice-service",
  "billing-service",
  "localization-service",
  "nginx-gateway"
)

docker compose @composeFiles up -d @services
