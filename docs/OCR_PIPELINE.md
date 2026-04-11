# OCR pipeline (`documents-service`)

## Поток

1. **Upload** → S3 (или LocalStack) + запись в PostgreSQL + постановка задачи Celery `ocr_processing_task`.
2. **Celery worker** → загрузка файла, OCR (`ocr_pipeline`), извлечение полей, опционально categorization-service, создание draft транзакции в `transactions-service`.
3. **Статусы документа** в БД: `processing` → `completed` / `failed`; поля review (`needs_review`, `review_reason`) при низкой уверенности.

## Ретраи

- Транзиентные ошибки S3/OCR: логирование (`logging` в worker); при необходимости включить Celery `autoretry_for` и backoff на уровне задачи (roadmap).
- Очередь: Redis (`CELERY_BROKER_URL`); при недоступности Redis upload может приниматься, но задача не выполнится — мониторить очередь.

## Health

- `GET /health` проверяет доступность БД (`SELECT 1`).
