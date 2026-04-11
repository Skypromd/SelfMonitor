#!/usr/bin/env bash
# Поднять только контур v1 MVP (см. docs/production-scope.md).
# Зависимости подтягиваются автоматически; «тяжёлые» профили (graphql, mlops, siem, dev-localstack) не включаются.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

EXTRA=()
if [[ "${USE_COMPOSE_PROD:-}" == "1" ]]; then
  EXTRA+=(-f docker-compose.prod.yml)
  if [[ -f .env.prod ]]; then
    EXTRA+=(--env-file .env.prod)
  fi
fi

# Явный список: порядок не критичен — compose разрулит зависимости.
SERVICES=(
  postgres-master
  redis-master
  redis
  minio
  vault
  categorization-service
  compliance-service
  consent-service
  auth-service
  user-profile-service
  transactions-service
  banking-connector
  documents-service
  celery-worker-docs
  weaviate
  qna-service
  integrations-service
  calendar-service
  tax-engine
  mtd-agent
  invoice-service
  billing-service
  localization-service
  nginx-gateway
)

docker compose -f docker-compose.yml "${EXTRA[@]}" up -d "${SERVICES[@]}"
