# Tax Engine Service

Calculates tax liabilities based on categorized transactions.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /calculate | Yes | Calculate tax liability for a given period and jurisdiction |
| POST | /calculate-and-submit | Yes | Calculate tax and submit to HMRC via integrations service |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| TRANSACTIONS_SERVICE_URL | No | http://localhost:8002/transactions/me | URL of the transactions service |
| INTEGRATIONS_SERVICE_URL | No | http://localhost:8010/integrations/hmrc/submit-tax-return | URL of the integrations HMRC endpoint |
| CALENDAR_SERVICE_URL | No | http://localhost:8015/events | URL of the calendar service |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
