# Analytics Service

Handles background analytical tasks and data analysis.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /jobs | Yes | Trigger a new analytics job (run_etl_transactions, train_categorization_model) |
| GET | /jobs/{job_id} | Yes | Retrieve the status of a specific job |
| POST | /forecast/cash-flow | Yes | Generate a cash-flow forecast |
| GET | /reports/mortgage-readiness | Yes | Generate a mortgage readiness PDF report |
| GET | /api/v1/marketplace/revenue | No | API marketplace revenue dashboard |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| ANALYTICS_DB_PATH | No | /tmp/analytics.db | Path to the SQLite analytics database |
| ANALYTICS_JOB_DURATION_SECONDS | No | 0.2 | Simulated job processing duration |
| API_MARKETPLACE_ENABLED | No | true | Enable/disable the API marketplace |
| TRANSACTIONS_SERVICE_URL | No | - | URL of the transactions service |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
