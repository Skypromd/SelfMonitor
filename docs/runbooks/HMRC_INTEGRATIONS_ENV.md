# Runbook: HMRC / integrations-service (env)

## Ключевые переменные

| Переменная | Назначение |
|------------|------------|
| `HMRC_ENV` | `sandbox` (default) или `production` — базовые URL API и OAuth. |
| `HMRC_DIRECT_API_BASE_URL` / `HMRC_OAUTH_TOKEN_URL` | Переопределение URL при необходимости. |
| `HMRC_DIRECT_SUBMISSION_ENABLED` | `true` только при готовых OAuth-клиентах и тестах sandbox/prod по процедуре HMRC. |
| `HMRC_REQUIRE_EXPLICIT_CONFIRM` | В проде **`true`**: цепочка draft → confirm → submit с `confirmation_token`. |
| `POLICY_SPEC_VERSION` | Версия политики, пишется в SQLite draft/confirm для аудита. |
| `HMRC_HTTP_MAX_RETRIES` / `HMRC_HTTP_RETRY_BACKOFF_SECONDS` | Ретраи на 429/502/503/504. |

## Идемпотентность и аудит

- Повторный submit с тем же **использованным** `confirmation_token` → **403** (токен помечается consumed).
- Новый submit требует новой пары draft → confirm.
- Correlation id: передавать в теле quarterly request (`correlation_id`).

## Ссылки

- `docs/POLICY_SPEC.md`
- `services/integrations-service/app/hmrc_mtd.py`
