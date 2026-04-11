# Целевая модель продакшена для Docker Compose

Документ фиксирует **как должен выглядеть** контур на Compose: окружения, блокеры v1, nginx, roadmap. Рабочий вход в репозитории:

| Файл | Назначение |
|------|------------|
| `docker-compose.yml` | Общая схема сервисов (dev-friendly порты). |
| `docker-compose.prod.yml` | Prod: billing том, restart, backup profile (**том Postgres уже в базовом** `docker-compose.yml`). |
| `docker-compose.staging.yml` | Staging: отдельное `name:` → изолированные volumes. |
| `nginx/nginx.conf` + `nginx/snippets/` | Gateway; общие proxy-заголовки в `proxy_common.conf`. |
| `.env.prod.example` / `.env.staging.example` | Шаблоны секретов (**не** коммитить `.env.prod` / `.env.staging`). |

### Рекомендуемое решение для v1 (MVP)

Не поднимать весь `docker-compose.yml` целиком: используйте скрипты **`scripts/compose_v1_up.sh`** или **`scripts/compose_v1_up.ps1`** — они запускают только сервисы из **`docs/production-scope.md`** (плюс их зависимости, без graphql/mlops/siem/localstack по умолчанию).

- Prod-override: `USE_COMPOSE_PROD=1 ./scripts/compose_v1_up.sh` (подхватит `docker-compose.prod.yml` и `.env.prod`, если есть).
- **QnA / Weaviate:** при **`USE_COMPOSE_PROD=1`** по умолчанию **`V1_INCLUDE_QNA_VECTOR=0`** (статический FAQ на фронте; вектор опционален). Включить вектор: `V1_INCLUDE_QNA_VECTOR=1`.
- **TLS:** целевой вариант — **снаружи** стека (Cloudflare, LB, nginx на хосте). **`security-proxy`** в compose — опция для полностью dockerized стенда, не обязателен для описанного prod-пути.
- **Vault (`server -dev`):** контейнер остаётся компромиссом для **banking-connector** в dev-like compose. Для реального prod планируйте **внешний** Vault / секреты и отказ от `-dev` в рантайме.
- **Бэкап Postgres:** `infra/backup/postgres-backup.sh` — `pg_dumpall` → gzip, ротация по mtime, **`POSTGRES_PASSWORD` обязателен**, пароль в лог не выводится.
- **Сверка «нет хардкода секретов» в YAML:** например `rg -n 'a_secure_|super-secret|redis_secure_password|minioadmin' docker-compose.yml` — ожидаемо остаются только **допустимые** вхождения (комментарии, переменные окружения с дефолтом `password` для локального Postgres, `:-minioadmin` для dev MinIO в отдельных ключах). Критичные JWT/Stripe/Vault-token в виде литералов в сервисах убраны ранее.

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

- **PostgreSQL:** `postgres-master` монтирует **`postgres_master_data`** (данные не теряются при пересоздании контейнера без удаления volume).
- Redis (пароль опционально: `REDIS_PASSWORD`; без него мастер без ACL-пароля — только для доверенной dev-сети), MinIO/S3.
- **nginx-gateway** — единая точка API для клиентов.

### 2.1 Профили (не поднимать «зоопарк» по умолчанию)

| Профиль | Сервисы |
|---------|---------|
| *(без профиля)* | Основной стек; **не** стартуют: graphql-gateway, postgres-replica, redis replicas/sentinels, localstack, aws-cli-setup, mlflow, elasticsearch/kibana. |
| `graphql` | `graphql-gateway` |
| `ha-postgres` | `postgres-replica` (эксперимент HA; для prod на Compose лучше один мастер + бэкапы). |
| `redis-ha` | `redis-replica-*`, `redis-sentinel-*` — пароль мастера должен совпадать с `masterauth` / Sentinel в `infra/redis/*.conf` или задайте `REDIS_PASSWORD` и синхронизируйте конфиги. |
| `dev-localstack` | LocalStack + `aws-cli-setup` (S3/Textract для dev OCR). Без профиля документы ходят в **MinIO**; Textract по умолчанию всё ещё указывает на localstack — для OCR включите профиль или смените endpoint. |
| `mlops` | `mlflow-server` |
| `siem` | `elasticsearch`, `kibana` |
| `backup` | `postgres-backup` (в `docker-compose.prod.yml` / staging). |

**nginx-gateway** `depends_on` сокращён до **контура v1** (`docs/production-scope.md`); остальные upstream поднимаются транзитивно или позже — при обращении к ним nginx резолвит имя.

## 3. Блокеры v1 (порядок)

### A. Секреты и конфиги

- Использовать `.env` / `.env.prod` (не в git) + **`.env.example`** в репозитории.
- В `docker-compose.yml` убраны захардкоженные JWT/сессии для **invoice-service**, **security-service**, **graphql-gateway** (через `AUTH_SECRET_KEY` / `GRAPHQL_JWT_SECRET`), **Vault token** без дефолта в YAML — задайте `VAULT_DEV_ROOT_TOKEN_ID` в `.env` для dev.
- **backup-service:** убран **`docker.sock`**; шифрование и S3 только если заданы `BACKUP_ENCRYPTION_KEY` / ключи S3.
- **DoD:** gitleaks зелёный; прод-значения только на сервере / в секрет-хранилище.

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
