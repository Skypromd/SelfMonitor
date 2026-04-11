# Runbook: сбои Stripe webhooks

## Симптомы

- Подписки не обновляются после оплаты
- В Stripe Dashboard webhook delivery **4xx/5xx**
- Расхождение плана в **billing-service** и **auth-service**

## Проверки

1. **billing-service** в prod: заданы **`STRIPE_SECRET_KEY`** и **`STRIPE_WEBHOOK_SECRET`**.
2. Endpoint доступен извне: `POST https://<your-domain>/api/billing/webhook` (точный путь см. nginx → billing).
3. Заголовок **`Stripe-Signature`** присутствует на реальных вызовах Stripe.
4. Логи billing на **`Invalid signature`** / **`503`** «webhook secret not configured».

## Идемпотентность

- Таблица **`stripe_webhook_events`** в SQLite billing DB: повтор того же **`event.id`** возвращает **`duplicate`** и **не** дублирует бизнес‑логику.
- Если событие «застряло», можно безопасно **переотправить** из Stripe Dashboard после исправления конфига.

## Типичные исправления

- Неверный **`STRIPE_WEBHOOK_SECRET`** (скопировать заново из Stripe).
- nginx режет body (проверить `client_max_body_size` для webhook — обычно достаточно).
- После деплоя перезапустить **nginx-gateway** если 502 на апстрим.

## Документы

- **`docs/BILLING_SUBSCRIPTION_LIFECYCLE.md`**
