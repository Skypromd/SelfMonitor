# Advice Service

Provides non-regulated financial insights.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /generate | Yes | Generate financial advice on a given topic (spending_analysis, savings_potential, income_protection) |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| TRANSACTIONS_SERVICE_URL | No | http://localhost:8002/transactions/me | URL of the transactions service |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
