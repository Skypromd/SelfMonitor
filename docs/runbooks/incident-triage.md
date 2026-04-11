# Runbook: первичный разбор инцидента (triage)

Цель за **5 минут**: понять **симптом**, **область**, **серьёзность**.

## 1. Классификация

| Уровень | Примеры |
|---------|---------|
| P0 | Нет авторизации, утечка данных, полная недоступность оплаты |
| P1 | Частичная деградация MTD/банкинга, высокий 5xx |
| P2 | Один второстепенный сервис, workaround есть |

## 2. Быстрые проверки

- Gateway **`/health`** и **`scripts/smoke_gateway_health.sh`**
- Grafana / Prometheus: 5xx, p95, ошибки webhook
- Логи **auth-service**, **billing-service**, **integrations-service** за окно инцидента

## 3. Собрать артефакты

- `X-Request-Id` / correlation id пользователя
- Время первого срабатывания алерта
- Версия деплоя (image tag / git sha)

## 4. Дальнейшие шаги

- Если релиз подозрителен — **`docs/runbooks/rollback.md`**
- Если БД — **`docs/runbooks/restore-db.md`**
- Stripe — **`docs/runbooks/stripe-webhook-failures.md`**

## 5. После стабилизации

Короткий postmortem: причина, что сделали, что предотвратит повтор.
