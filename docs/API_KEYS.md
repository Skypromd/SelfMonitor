# API keys (auth-service)

Доступно для планов с **`api_access: true`** в `PLAN_FEATURES` (сейчас **Pro** и **Business**).

## Создание и отзыв (пользователь с JWT)

За nginx gateway префикс обычно `/api/auth/`:

| Метод | Путь | Описание |
|--------|------|----------|
| POST | `/api-keys` | Создать ключ; в ответе **полный** `api_key` только один раз. |
| GET | `/api-keys` | Список ключей (без секрета). |
| DELETE | `/api-keys/{key_id}` | Отозвать (`key_id` — 32 hex-символа из ответа создания). |

## Обмен на access token (для клиентов API)

`POST /token/api-key` с телом:

```json
{ "api_key": "smk_<32_hex_key_id>_<secret>" }
```

Ответ как у логина: `{ "access_token": "...", "token_type": "bearer" }`. Дальше все вызовы — с `Authorization: Bearer <access_token>`.

## Прод

- Храните ключи только в секрет-хранилищах; не логируйте.
- **nginx-gateway:** для `POST /api/auth/token/api-key` включён отдельный **rate limit** (`api_key_exchange_per_ip`, по умолчанию ~10 запросов/мин с одного IP; см. `nginx/nginx.conf`).
- Успешный обмен ключа на JWT пишет событие **`api_key_exchanged`** в **`security_events`** (`auth-service`) с `key_id` и IP/User-Agent (если есть).
- Отозванные ключи (`revoked_at`) не принимаются.
