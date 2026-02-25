# Predictive Analytics Service

ML-powered churn prediction and retention optimization.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /churn-prediction/{user_id} | Yes | Predict churn risk for a specific user |
| GET | /cohort-churn-analysis | Yes | Analyze churn patterns across user cohorts |
| POST | /intervention-campaigns/{campaign_type} | Yes | Launch targeted retention campaigns |
| GET | /ml-model-performance | Yes | Get performance metrics for churn prediction ML models |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
