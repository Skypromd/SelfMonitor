# Runbook: откат релиза приложения

## Kubernetes (типично)

1. Откатить Deployment на предыдущий **image tag** / **helm revision**:
   - `helm rollback <release> [revision]`
   - или `kubectl rollout undo deployment/<name>`
2. Убедиться, что **миграции** обратно совместимы; если нет — сначала откат миграций по отдельной процедуре (редко, избегать breaking schema в одном релизе).

## Docker Compose (staging / простой прод)

1. Зафиксировать **теги образов** в `.env` / override файле.
2. `docker compose pull && docker compose up -d` с предыдущими тегами.
3. Перезапустить **nginx-gateway** после апстримов (см. `AGENTS.md` gotcha DNS).

## Проверка после отката

- `scripts/smoke_gateway_health.sh`
- Критичный пользовательский путь вручную.

## Коммуникация

- Уведомить stakeholders; зафиксировать причину отката для postmortem.
