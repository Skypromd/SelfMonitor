# Стандарт сервиса (SelfMonitor)

Единые ожидания для сервисов в **`services/*`**, чтобы не плодить 20 разных стилей.

## Обязательно (целевое состояние; новые изменения — сразу по стандарту)

### HTTP API

- **`GET /health`** — liveness: процесс жив; **200** `{"status": "ok"}` минимум.
- **`GET /ready`** (рекомендуется для сервисов с БД/Redis/очередью) — readiness: критичные зависимости доступны; **503** если нет.
- Версия в OpenAPI: поле **`version`** в FastAPI `title` / description.

### Ошибки

Единый JSON (цель для новых эндпоинтов):

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Human readable",
  "details": {},
  "trace_id": "optional-correlation-id"
}
```

Пока допустим legacy `{"detail": "..."}` — постепенно выравнивать.

### Идентификация запроса

- Принимать заголовок **`X-Request-Id`** от **nginx-gateway** (или генерировать в приложении, если вызов внутренний).
- Логировать **`request_id`** в одном поле structured log.

### Таймауты исходящих HTTP

- Явные **timeouts** (connect + read); **retry** только на идемпотентных GET или с idempotency-key (как Stripe/HMRC интеграции).

### Секреты

- Нет дефолтных прод‑секретов в коде; при отсутствии критичного env — **fail fast** при старте (где применимо).

### Миграции

- **Alembic** (или эквивалент) — единственный источник схемы в **prod**; не полагаться на `create_all` в проде.

## Наблюдаемость

- **Prometheus** `/metrics` — по возможности для сервисов за gateway.
- Логи: **не** писать полные JWT, пароли, полные номера карт, сырой PII.

## Ссылки

- **`docs/HEALTH_ENDPOINTS.md`**
- **`docs/production-scope.md`**
- Библиотеки (roadmap): `libs/shared_http`, `libs/observability` — вынести общие middleware по мере роста.

*Последнее обновление: 2026-04-10.*
