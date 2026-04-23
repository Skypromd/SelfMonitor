# Integrations Service

Facades external API integrations.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /integrations/hmrc/submit-tax-return | Yes | Submit a tax return to HMRC |
| GET | /integrations/hmrc/submissions/{submission_id} | Yes | Get the status of an HMRC submission |
| GET | /integrations/hmrc/submissions | Yes | List all HMRC submissions for the current user |
| GET | /integrations/hmrc/self-assessment/{tax_year}/calculations | Yes | List Self Assessment tax calculations (HMRC Individual Calculations API; `tax_year` like `2024-25`) |
| POST | /integrations/hmrc/self-assessment/{tax_year}/calculations/trigger | Yes | Trigger a calculation (`in-year`, `intent-to-finalise`, `end-of-year`) |
| GET | /integrations/hmrc/self-assessment/{tax_year}/calculations/{calculation_id} | Yes | Retrieve full calculation JSON |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| COMPLIANCE_SERVICE_URL | No | (empty) | Base URL of compliance-service; when set, posts audit events (`cis_unverified_submit_confirmed`, `mtd_quarterly_submitted`, `mtd_final_declaration_submitted`) |
| INTEGRATIONS_DB_PATH | No | `/tmp/integrations.db` | Writable path for SQLite (required in Docker; app default matches this) |
| INTEGRATIONS_PROCESSING_DELAY_SECONDS | No | 0.25 | Simulated HMRC processing delay |
| HMRC_DIRECT_SUBMISSION_ENABLED | No | false | When true, MTD quarterly + Individual Calculations call HMRC (sandbox/prod base URLs) |
| HMRC_OAUTH_SCOPE | No | `read:self-assessment write:self-assessment` | OAuth scope for client-credentials token (list/retrieve need read) |
| HMRC_INDIVIDUAL_CALCULATIONS_ACCEPT | No | `application/vnd.hmrc.8.0+json` | Accept header for Individual Calculations API version |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

`app.main` adds the monorepo root to `sys.path` when it finds a `libs/` directory, so you can run pytest from `services/integrations-service` without setting `PYTHONPATH`. CI still sets `PYTHONPATH` to the workspace root for consistency with other services.

```bash
cd services/integrations-service
pytest tests/test_main.py
```
