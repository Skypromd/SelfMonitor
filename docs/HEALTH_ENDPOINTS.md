# Health endpoints — контракт

## Общее- **Успех:** HTTP200, JSON с минимумом `{"status": "ok"}`.
- **Деградация:** сервис может отвечать 503 с `status: degraded` и кратким `detail`, если критичная зависимость недоступна (политика команды).

## Критичные сервисы (рекомендуемый smoke через nginx `:8000`)

| Сервис | Путь за gateway | Примечание |
|--------|-----------------|------------|
| nginx (косвенно) | Любой успешный `/api/*/health` | Единая точка входа |
| auth-service | `/api/auth/health` | Проверить актуальный префикс в `nginx.conf` |
| billing-service | `/api/billing/health` | |
| transactions-service | `/api/transactions/health` | По факту маршрутизации |
| documents-service | `/api/documents/health` | Включает проверку БД (`database: connected` при успехе) |
| integrations-service | `/api/integrations/health` | HMRC-интеграции |
| invoice-service | `/api/invoices/health` | |
| banking-connector | `/api/banking/health` | Префикс см. nginx |

Точные `location` см. `nginx/nginx.conf`. Исключения (нет `/health`) должны быть перечислены здесь при появлении.

## Скрипт smoke

После `docker compose up -d`: `scripts/smoke_gateway_health.ps1` или `scripts/smoke_gateway_health.sh`.
