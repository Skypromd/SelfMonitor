# Subscriptions (MVP)

## Plans
- **Free**: Monthly summaries, CSV import, basic tax estimate.
- **Pro**: Quarterly summaries, tax-year summary, profit & loss, mortgage report, HMRC submission.

## Billing cadence
- Monthly billing cycle (default).
- `current_period_start` and `current_period_end` are stored on the user profile.

## Endpoints (user-profile-service)
```
GET /subscriptions/me
PUT /subscriptions/me
POST /billing/webhook
```

## Stripe billing (Payment Links + Webhooks)
Set these environment variables on the user-profile-service:
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_PRO_MONTHLY_ID`
- `STRIPE_PRICE_PRO_ANNUAL_ID`

Mobile app Payment Links (Expo env):
- `EXPO_PUBLIC_STRIPE_CHECKOUT_URL`
- `EXPO_PUBLIC_STRIPE_CHECKOUT_ANNUAL_URL`
- `EXPO_PUBLIC_STRIPE_PORTAL_URL`

Webhook events handled:
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `checkout.session.completed` (fallback)

## Plan gating (align with `auth-service` `PLAN_FEATURES`)
- **HMRC MTD guided submit** (draft → confirm): paid tiers Starter+ (`hmrc_submission`).
- **Live HMRC with strict fraud `client_context`**: **Pro+** only (`hmrc_direct_submission` in JWT; see `integrations-service`).
- **VAT returns (prepare/submit)**: **Pro+** (`vat_returns`).
- **Mortgage / advanced analytics / API**: largely **Pro+** — see `docs/PLAN_FEATURES_TABLE.md`.

Legacy **Pro-only** report routes (enforce in `transactions-service` / web as needed):
- `GET /reports/quarterly-summary`
- `GET /reports/profit-loss`
- `GET /reports/tax-year-summary`
- `GET /reports/mortgage-readiness`
- `POST /calculate-and-submit` (checks plan via gateway/auth)

## Notes
This MVP uses Stripe Payment Links + webhook syncing to update subscription status.
