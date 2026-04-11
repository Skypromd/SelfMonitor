#!/usr/bin/env bash
# Поднять v1 бэкенд для web-portal (nginx-gateway :8000). Нужен работающий Docker.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! docker info >/dev/null 2>&1; then
  echo "Docker не отвечает. Запустите демон и повторите." >&2
  exit 1
fi

"$ROOT/scripts/compose_v1_up.sh"

echo "Ожидание :8000..."
ok=0
for i in $(seq 1 60); do
  if curl -sf "http://localhost:8000/health" >/dev/null; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" -eq 1 ]]; then
  echo "Gateway OK: http://localhost:8000 — можно npm run dev в apps/web-portal"
else
  echo "Health на :8000 не ответил. Смотрите: docker compose logs nginx-gateway" >&2
  exit 1
fi
