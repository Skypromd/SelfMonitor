# Postgres backup в Compose (profile `backup`)

## Запуск

С prod merge:

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d postgres-backup
```

Скрипт: `infra/backup/postgres-backup.sh` — ожидает здоровый `postgres-master`, затем в цикле делает `pg_dumpall | gzip`.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `POSTGRES_HOST` | `postgres-master` | Хост БД в сети compose |
| `POSTGRES_USER` | `user` | |
| `POSTGRES_PASSWORD` | — | обязательна |
| `BACKUP_RETENTION_DAYS` | `14` | удаление `*.sql.gz` старше N дней (mtime) |
| `BACKUP_INTERVAL_SEC` | `86400` | пауза между дампами |

## Где лежат файлы

Docker volume **`postgres_backups`** (имя проекта префиксуется, например `selfmonitor-prod_postgres_backups`).

Список с хоста:

```bash
docker run --rm -v selfmonitor-prod_postgres_backups:/backups alpine ls -la /backups
```

Подставьте имя volume из `docker volume ls`.

## Копия в облако

Добавьте cron на хосте: `docker run ... cp` / `rclone` / `aws s3 sync` с каталога, смонтированного в тот же volume.

См. **`docs/runbooks/restore-db.md`** для восстановления.
