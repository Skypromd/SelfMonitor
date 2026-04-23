# Banking Connector Service

Service for connecting to Open Banking providers and fetching data.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /connections/initiate | Yes | Initiate a connection with a banking provider |
| GET | /connections/callback | Yes | Handle the OAuth callback from a banking provider |
| GET | /accounts/{account_id}/transactions | No (deprecated) | Get transactions for an account (deprecated) |
| GET | /exports/statement-csv | Yes | CSV of stored transactions (default last 180 days) from transactions-service; read-only, no sync slot |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| TRANSACTIONS_SERVICE_URL | Yes (import) | `http://transactions-service/import` | Celery POST target for imported rows |
| TRANSACTIONS_ME_URL | No | derived from `TRANSACTIONS_SERVICE_URL` | GET list for `/exports/statement-csv` (override if import URL is non-standard) |
| VAULT_ADDR | No | - | HashiCorp Vault address for token storage |
| VAULT_TOKEN | No | - | HashiCorp Vault authentication token |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pytest -q tests/test_banking_connector_main.py
```

Use a project venv so third-party global pytest plugins do not break the suite. If you still see `pytest_flask` import errors against Flask 3, uninstall `pytest-flask` from that environment or set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` for the pytest run only.
