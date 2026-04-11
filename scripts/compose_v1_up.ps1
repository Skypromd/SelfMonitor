# Поднять только контур v1 MVP (см. docs/production-scope.md).
# QnA+Weaviate: при USE_COMPOSE_PROD=1 по умолчанию отключены (V1_INCLUDE_QNA_VECTOR=0); в dev — включены.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$composeFiles = @("-f", "docker-compose.yml")
if ($env:USE_COMPOSE_PROD -eq "1") {
  $composeFiles += "-f", "docker-compose.prod.yml"
  if (Test-Path ".env.prod") {
    $composeFiles += "--env-file", ".env.prod"
  }
  if (-not $env:V1_INCLUDE_QNA_VECTOR) {
    $env:V1_INCLUDE_QNA_VECTOR = "0"
  }
}
elseif (-not $env:V1_INCLUDE_QNA_VECTOR) {
  $env:V1_INCLUDE_QNA_VECTOR = "1"
}

$services = [System.Collections.ArrayList]@(
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
  "integrations-service",
  "calendar-service",
  "tax-engine",
  "mtd-agent",
  "invoice-service",
  "billing-service",
  "localization-service"
)

if ($env:V1_INCLUDE_QNA_VECTOR -eq "1") {
  [void]$services.Add("weaviate")
  [void]$services.Add("qna-service")
}

[void]$services.Add("nginx-gateway")

docker compose @composeFiles up -d @services
