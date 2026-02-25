# Referral Service

Manages referral codes, rewards, and viral growth campaigns.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /referral-codes | Yes | Generate a unique referral code for the user |
| POST | /validate-referral | Yes | Validate and apply a referral code during registration |
| GET | /stats | Yes | Get referral statistics for the user |
| GET | /leaderboard | Yes | Get top referrers leaderboard |
| POST | /campaigns/{campaign_id}/join | Yes | Join a special referral campaign |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| DATABASE_URL | No | postgresql+asyncpg://user:password@localhost/db_referral | PostgreSQL connection string |
| USER_PROFILE_SERVICE_URL | No | http://localhost:8001 | URL of the user profile service |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
