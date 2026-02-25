# Compliance Service

Handles audit logs and other compliance tasks.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /audit-events | Yes | Record a new event in the persistent audit log |
| GET | /audit-events | Yes | Query the audit log, optionally filtered by user_id |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| DATABASE_URL | No | postgresql+asyncpg://user:password@localhost/db_compliance | PostgreSQL connection string |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
