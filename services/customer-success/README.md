# Customer Success Service

Automated customer onboarding, churn prediction, and proactive success management.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /user-journey/{user_id} | Yes | Analyze a user's current onboarding journey stage |
| POST | /proactive-intervention | Yes | Trigger proactive interventions for at-risk users |
| GET | /success-metrics/{user_id} | Yes | Get comprehensive success metrics for a user |
| GET | /cohort-analysis | Yes | Analyze user cohorts for retention patterns |
| POST | /automated-success-campaigns/{campaign_type} | Yes | Launch automated success campaigns |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| USER_PROFILE_SERVICE_URL | No | http://localhost:8001 | URL of the user profile service |
| TRANSACTIONS_SERVICE_URL | No | http://localhost:8002 | URL of the transactions service |
| ANALYTICS_SERVICE_URL | No | http://localhost:8012 | URL of the analytics service |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
