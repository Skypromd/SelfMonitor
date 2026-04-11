#!/usr/bin/env bash
# Поднять только контур v1 MVP (см. docs/production-scope.md).
# Зависимости подтягиваются автоматически; «тяжёлые» профили (graphql, mlops, siem, dev-localstack) не включаются.
#
# QnA + Weaviate (векторный поиск): по умолчанию включаются в dev. Для prod-контура без вектора:
#   USE_COMPOSE_PROD=1 V1_INCLUDE_QNA_VECTOR=0 ./scripts/compose_v1_up.sh
# (или явно V1_INCLUDE_QNA_VECTOR=0). Статический FAQ на фронте; /api/qna вернёт 502, пока не поднят qna.
#
# Vault в compose — dev-режим (server -dev). Целевой prod: внешний секрет-хранилище + уход от dev-vault (см. docs/COMPOSE_PRODUCTION.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

EXTRA=()
if [[ "${USE_COMPOSE_PROD:-}" == "1" ]]; then
  EXTRA+=(-f docker-compose.prod.yml)
  if [[ -f .env.prod ]]; then
    EXTRA+=(--env-file .env.prod)
  fi
  : "${V1_INCLUDE_QNA_VECTOR:=0}"
else
  : "${V1_INCLUDE_QNA_VECTOR:=1}"
fi

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
  integrations-service
  calendar-service
  tax-engine
  mtd-agent
  invoice-service
  billing-service
  localization-service
)

if [[ "${V1_INCLUDE_QNA_VECTOR}" == "1" ]]; then
  SERVICES+=(weaviate qna-service)
fi

SERVICES+=(nginx-gateway)

docker compose -f docker-compose.yml "${EXTRA[@]}" up -d "${SERVICES[@]}"
