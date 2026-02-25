# Transactions Service

Stores and categorizes financial transactions.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /import | Yes | Import a batch of transactions for an account |
| GET | /accounts/{account_id}/transactions | Yes | Get all transactions for a specific account |
| GET | /transactions/me | Yes | Get all transactions for the authenticated user |
| PATCH | /transactions/{transaction_id} | Yes | Update the category of a transaction |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| DATABASE_URL | No | postgresql+asyncpg://user:password@localhost/db_transactions | PostgreSQL connection string |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
