# Consent Service

Manages user consents for data access.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /consents | Yes | Record a new user consent for a connection |
| GET | /consents | Yes | List all active consents for the authenticated user |
| GET | /consents/{consent_id} | Yes | Retrieve a specific consent by ID |
| DELETE | /consents/{consent_id} | Yes | Revoke a user's consent |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| COMPLIANCE_SERVICE_URL | No | http://localhost:8003/audit-events | URL of the compliance service audit endpoint |
| CONSENT_DB_PATH | No | /tmp/consent.db | Path to the SQLite consent database |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
