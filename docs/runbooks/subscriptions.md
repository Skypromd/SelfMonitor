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
```

## Pro gating
The following endpoints require a Pro subscription:
- `GET /reports/quarterly-summary`
- `GET /reports/profit-loss`
- `GET /reports/tax-year-summary`
- `GET /reports/mortgage-readiness`
- `POST /calculate-and-submit` (HMRC submission)

## Notes
This MVP uses profile storage for subscriptions. Real billing (Stripe) can be added later.
