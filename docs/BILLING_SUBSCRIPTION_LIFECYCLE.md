# Жизненный цикл подписки (billing ↔ auth)

## Состояния (целевая модель)

| Состояние | Описание |
|-----------|----------|
| **trialing** | Пробный период (Stripe trial или внутренний trial). |
| **active** | Оплаченная активная подписка. |
| **past_due** | Платёж не прошёл; ограниченный grace (если включите в Stripe). |
| **canceled** | Пользователь отменил; доступ до конца оплаченного периода по политике. |
| **expired** | Trial/период истёк; план должен уйти в `free` или заблокированный режим. |

## Синхронизация

- **Источник оплаты:** `billing-service` (Stripe webhooks).
- **Источник entitlements в API:** `auth-service` выдаёт JWT с `plan` и лимитами из **`PLAN_FEATURES`** (см. `docs/PLAN_FEATURES_TABLE.md`).
- После webhook `checkout.session.completed` / `customer.subscription.updated` billing должен вызывать или согласовывать состояние с auth (текущая реализация — см. код `billing-service`).

## Downgrade / expiry

- При переходе на более низкий план или `free`: лимиты из нового плана применяются на **следующем** выпуске JWT (refresh/login).
- Документы/транзакции выше квоты: политика «read-only / no new uploads» — зафиксировать продуктово; тесты — по мере внедрения.

## Прод

- Включить реальные `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, проверить подпись webhook и идемпотентность обработки событий.
- Реализация в **`billing-service`**: при заданном `STRIPE_SECRET_KEY` webhook **требует** заголовок `Stripe-Signature` и валидную подпись; повторная доставка того же `event.id` сохраняется в **`stripe_webhook_events`** и отвечается `duplicate` без повторной обработки.
