# Runbook: восстановление PostgreSQL (шаблон)

Адаптируйте под вашего провайдера (RDS, Cloud SQL, self-hosted).

См. также **`docs/COMPOSE_PRODUCTION.md`**, бэкап: **`docs/runbooks/compose-postgres-backup.md`**.

## Подготовка

1. Остановить запись в приложение (maintenance mode / scale deployments to 0) — **если** нужна консистентность.
2. Выбрать **точку восстановления** (snapshot / dump timestamp).

## Восстановление из дампа

```bash
# Пример: восстановление в новую БД или поверх после DROP (ОПАСНО в проде — только по процедуре)
pg_restore -h <host> -U <user> -d <database> -v backup.dump
# или
psql -h <host> -U <user> -d <database> -f backup.sql
```

## Docker Compose (dump от `postgres-backup`)

Контейнер БД в репозитории: **`postgres_master`** (сервис `postgres-master`). Дамп sidecar: **`pg_dumpall`** → **`/backups/pg_all_<timestamp>.sql.gz`** в volume `postgres_backups`.

1. Скопируйте архив с volume на хост (пример, подставьте имя volume из `docker volume ls`):

```bash
docker run --rm -v selfmonitor-prod_postgres_backups:/backups -v "$PWD:/out" alpine \
  cp /backups/pg_all_2026-04-10T120000.sql.gz /out/
gzip -d pg_all_2026-04-10T120000.sql.gz
```

2. Остановите приложения, пишущие в Postgres (или весь стек), чтобы не было записи во время restore.

3. Залейте SQL в кластер (восстанавливает **все** БД из дампа `pg_dumpall`):

```bash
# Из каталога с репозиторием, сеть default_network уже создана compose
docker run --rm -i \
  -e PGPASSWORD="$POSTGRES_PASSWORD" \
  -v "$PWD:/restore:ro" \
  --network selfmonitor-prod_default_network \
  postgres:15-alpine \
  psql -h postgres-master -U "${POSTGRES_USER:-user}" -f /restore/pg_all_2026-04-10T120000.sql
```

Имя сети может отличаться: `docker network ls | grep selfmonitor`.

4. Поднимите стек и пройдите smoke.

**Одна БД** (если дампили только её): используйте `pg_dump`/`pg_restore` для конкретного `-d db_name`.

## После restore

1. Запустить **миграции** в режиме «только проверка» или `alembic upgrade head` если схема отстаёт.
2. Проверить **`/ready`** критичных сервисов.
3. Smoke через gateway: **`scripts/smoke_gateway_health.sh`**.

## Откат

Если restore некорректен — вернуться к предыдущему snapshot и повторить по runbook **rollback** приложения.

См. также **`docs/disaster-recovery.md`**.
