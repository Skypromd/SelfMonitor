# Partner Registry Service

Manages a registry of third-party partners.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /partners | No | List all partners, optionally filtered by service type |
| GET | /partners/{partner_id} | No | Retrieve details for a specific partner |
| POST | /partners/{partner_id}/handoff | Yes | Initiate a handoff to a partner |
| GET | /handoffs | Yes | List handoff records for the current user |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| COMPLIANCE_SERVICE_URL | No | http://localhost:8003/audit-events | URL of the compliance service audit endpoint |
| PARTNERS_CATALOG_PATH | No | app/partners.json | Path to the partners JSON catalog |
| PARTNER_DB_PATH | No | /tmp/partner_registry.db | Path to the SQLite partner database |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
