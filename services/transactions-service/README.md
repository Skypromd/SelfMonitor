# Transactions Service

Stores and categorizes financial transactions.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /businesses | Yes | List businesses for the user (auto-creates **Primary**). |
| POST | /businesses | Yes | Create an extra business (**Business** plan only, max 10 total). |
| PATCH | /businesses/{business_id} | Yes | Rename a business you own. |
| POST | /import | Yes | Import a batch of transactions for an account (scoped by **`X-Business-Id`** UUID, optional → Primary). |
| GET | /accounts/{account_id}/transactions | Yes | Get transactions for an account (**`X-Business-Id`** scope). |
| GET | /transactions/me | Yes | Get transactions for the user (**`X-Business-Id`** scope). |
| PATCH | /transactions/{transaction_id} | Yes | Update the category of a transaction (**`X-Business-Id`** scope). |
| GET | /cis/evidence-pack/manifest | Yes | CIS evidence manifest (plan tier) |
| GET | /cis/evidence-pack/zip | Yes | CIS evidence ZIP download |
| POST | /cis/evidence-pack/share-token | Yes | Mint time-limited signed token for accountant download |
| GET | /cis/evidence-pack/shared-zip | No | Download CIS evidence ZIP using `token` query (signed with `INTERNAL_SERVICE_SECRET`); optional compliance audit |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| INTERNAL_SERVICE_SECRET | Yes | - | Also used to sign CIS evidence share tokens |
| COMPLIANCE_SERVICE_URL | No | (empty) | When set, shared ZIP download posts `cis_evidence_pack_shared_download` |
| CIS_EVIDENCE_SHARE_TOKEN_HOURS | No | 72 | Hours until share token expires |
| DATABASE_URL | No | postgresql+asyncpg://user:password@localhost/db_transactions | PostgreSQL connection string |

## Running Locally

From the monorepo root, set `PYTHONPATH` to the repository root (same as CI) so `libs.*` resolves.

```bash
export PYTHONPATH="$(pwd)"   # Windows PowerShell: $env:PYTHONPATH = (Get-Location).Path
cd services/transactions-service
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_transactions_service_main.py
```
