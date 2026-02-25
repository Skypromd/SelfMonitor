# User Profile Service

Manages user profile data.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /profiles/me | Yes | Retrieve the profile for the authenticated user |
| PUT | /profiles/me | Yes | Create or update the profile for the authenticated user |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| DATABASE_URL | No | postgresql+asyncpg://user:password@localhost/db_user_profile | PostgreSQL connection string |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
