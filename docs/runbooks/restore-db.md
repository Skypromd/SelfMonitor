# Runbook: восстановление PostgreSQL (шаблон)

Адаптируйте под вашего провайдера (RDS, Cloud SQL, self-hosted).

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

## После restore

1. Запустить **миграции** в режиме «только проверка» или `alembic upgrade head` если схема отстаёт.
2. Проверить **`/ready`** критичных сервисов.
3. Smoke через gateway: **`scripts/smoke_gateway_health.sh`**.

## Откат

Если restore некорректен — вернуться к предыдущему snapshot и повторить по runbook **rollback** приложения.

См. также **`docs/disaster-recovery.md`**.
