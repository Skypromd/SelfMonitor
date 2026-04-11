# Roadmap: REST API keys, partners, compliance trail

Часть чеклиста `docs/TODO_PRODUCTION.md` (§13–14) **не реализована в коде**; здесь зафиксированы направления.

## REST API (Pro)

- API keys: реализовано в **`auth-service`** (см. **`docs/API_KEYS.md`**); scope по эндпоинтам — roadmap.
- Rate limits: nginx / API gateway / middleware в сервисе.
- Audit log: user/key, маршрут, timestamp, correlation id — отдельное хранилище или поток событий.

## Partner / referral

- Правила начислений и модерация в **`partner-registry`** / **`referral-service`** — после продуктового sign-off.

## Compliance trail

- Централизованный audit поверх **`compliance-service`**: экспорт, сроки хранения, связка с MTD confirmation tokens и banking sync (см. policy spec).
