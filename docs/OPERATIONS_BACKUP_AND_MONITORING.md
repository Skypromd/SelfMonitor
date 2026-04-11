# Операции: бэкапы и мониторинг (шаблон)

## Резервное копирование

- **PostgreSQL:** снимки по расписанию (pg_dump / WAL / облачный managed backup).
- **Объектное хранилище (документы):** версионирование + cross-region replication по политике.
- **План восстановления:** RTO/RPO задокументировать; ежегодный тест restore на staging.

## Мониторинг

- Метрики: 5xx rate, p95 latency по gateway, HMRC submit success, длина очереди Celery (OCR), ошибки Stripe webhook.
- Алерты: Pager/Ops канал при деградации SLO из `integrations-service` (`/integrations/hmrc/mtd/submission-slo`).
