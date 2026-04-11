# Целевая модель продакшена для Docker Compose

Документ фиксирует **как должен выглядеть** контур на Compose: окружения, блокеры v1, nginx, roadmap. Рабочий вход в репозитории:

| Файл | Назначение |
|------|------------|
| `docker-compose.yml` | Общая схема сервисов (dev-friendly порты). |
| `docker-compose.prod.yml` | Prod: тома Postgres/billing, restart, backup profile. |
| `docker-compose.staging.yml` | Staging: отдельное `name:` → изолированные volumes. |
| `nginx/nginx.conf` + `nginx/snippets/` | Gateway; общие proxy-заголовки в `proxy_common.conf`. |
| `.env.prod.example` / `.env.staging.example` | Шаблоны секретов (**не** коммитить `.env.prod` / `.env.staging`). |

Проверка слияния:

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config
```

Запуск с бэкапами:

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d
```

## 1. Окружения

- **prod:** отдельный сервер(а), свой домен, TLS на edge, отдельные секреты.
- **staging:** тот же compose merge, другие `name:`, `.env`, домены, обычно меньше retention бэкапов.

## 2. Инфраструктура в Compose (обязательный минимум)

- PostgreSQL (в проде предпочтительно managed; в `docker-compose.prod.yml` включён том данных мастера).
- Redis, объектное хранилище (MinIO/S3).
- **nginx-gateway** — единая точка API для клиентов.

## 3. Блокеры v1 (порядок)

### A. Секреты и конфиги

- Использовать `.env.prod` (не в git) + шаблон `.env.prod.example`.
- Для чувствительных значений на хосте: файлы с правами root-only (например `/etc/selfmonitor/secrets/...`) или менеджер секретов; проброс в контейнеры через `env_file` / secrets driver.
- **DoD:** gitleaks зелёный; без обязательных секретов сервисы не должны молча работать как «прод» (fail-fast по мере внедрения в сервисах).

### B. Бэкапы и restore drill

- Сервис **`postgres-backup`** (profile `backup`): `pg_dumpall` → `gzip` в volume `postgres_backups`, ротация по `BACKUP_RETENTION_DAYS`.
- Точные команды восстановления: **`docs/runbooks/restore-db.md`**.
- **DoD:** есть файл бэкапа; restore на staging выполнен; `scripts/smoke_gateway_health.sh` проходит.

### C. Stripe prod (billing)

- Публичный webhook: **`POST https://<домен>/api/billing/webhook`** (префикс `/api/billing/` снимает nginx, в сервис попадает `/webhook`).
- Идемпотентность: таблица **`stripe_webhook_events`** в БД billing; в prod монтируйте **`BILLING_DB_PATH`** на том (`docker-compose.prod.yml`), иначе данные потеряются при пересоздании контейнера.
- Проверить TLS, размер тела, таймауты, доступность извне.
- **DoD:** тестовая оплата → webhook → план обновился → повтор события не создаёт дубль.

### D. Наблюдаемость (минимум)

- **X-Request-Id:** nginx отдаёт клиенту заголовок и пишет **`request_id`** в JSON access log; upstream получает тот же id через `proxy_common.conf`.
- Дальше: единый `request_id` в логах приложений; на VPS — дисциплина `docker compose logs` или стек Loki/Promtail.

## 4. Nginx (сделано в репо)

- Проксирование с **`include /etc/nginx/snippets/proxy_common.conf`** (и `proxy_ws.conf` для WebSocket).
- **`add_header X-Request-Id $correlation_request_id always;`** на уровне server.
- Поле **`request_id`** в `waf_json` access log.

## 5. Ограничение Compose merge

При merge двух файлов списки **`ports`** у сервисов **объединяются**, а не заменяются. В базовом `docker-compose.yml` у части сервисов по-прежнему опубликованы dev-порты. Для «только gateway наружу» используйте firewall/security group на хосте или отдельный «урезанный» compose для железа.

## 6. Roadmap ~10 дней (критерии)

| Окно | Фокус | Готово когда |
|------|--------|----------------|
| Дни 1–2 | Prod config hygiene: `.env.prod`, merge файлов, firewall | `compose config` валиден; снаружи только нужные порты. |
| Дни 3–4 | Backup + restore drill | Restore на staging выполнен, задокументирован. |
| Дни 5–7 | Stripe prod webhook + idempotency | Оплата и повтор webhook проверены. |
| Дни 8–10 | HMRC sandbox E2E + OCR smoke | По одному happy path по инструкции. |

См. также **`docs/TODO_PRODUCTION.md`**, **`docs/production-scope.md`**, **`docs/runbooks/stripe-webhook-failures.md`**.
