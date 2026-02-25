# Banking Connector Service

Service for connecting to Open Banking providers and fetching data.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /connections/initiate | Yes | Initiate a connection with a banking provider |
| GET | /connections/callback | Yes | Handle the OAuth callback from a banking provider |
| GET | /accounts/{account_id}/transactions | No (deprecated) | Get transactions for an account (deprecated) |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| VAULT_ADDR | No | - | HashiCorp Vault address for token storage |
| VAULT_TOKEN | No | - | HashiCorp Vault authentication token |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
