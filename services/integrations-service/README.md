# Integrations Service

Facades external API integrations.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /integrations/hmrc/submit-tax-return | Yes | Submit a tax return to HMRC |
| GET | /integrations/hmrc/submissions/{submission_id} | Yes | Get the status of an HMRC submission |
| GET | /integrations/hmrc/submissions | Yes | List all HMRC submissions for the current user |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| INTEGRATIONS_DB_PATH | No | /tmp/integrations.db | Path to the SQLite integrations database |
| INTEGRATIONS_PROCESSING_DELAY_SECONDS | No | 0.25 | Simulated HMRC processing delay |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
