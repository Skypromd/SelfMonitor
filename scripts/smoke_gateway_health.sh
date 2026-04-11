#!/usr/bin/env bash
# Smoke health checks through nginx gateway (default http://localhost:8000).
set -euo pipefail
BASE="${GATEWAY_URL:-http://localhost:8000}"
paths=(
  "/api/auth/health"
  "/api/billing/health"
  "/api/transactions/health"
  "/api/documents/health"
  "/api/integrations/health"
  "/api/invoices/health"
  "/api/banking/health"
  "/api/tax/health"
)
for p in "${paths[@]}"; do
  url="${BASE}${p}"
  echo "GET $url"
  curl -sSf "$url" >/dev/null
done
echo "All gateway health checks passed."
