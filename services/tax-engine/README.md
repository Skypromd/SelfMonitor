# Tax Engine Service

Calculates tax liabilities based on categorized transactions.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /calculate | Yes | Calculate tax liability for a given period and jurisdiction |
| POST | /mtd/prepare | Yes | Same calculation as `/calculate` plus `hmrc_period_summary_json` (shared MTD shape) and optional `integrations_quarterly_payload`; when `COMPLIANCE_SERVICE_URL` is set, emits audit `tax_mtd_prepare` |
| POST | /calculate-and-submit | Yes | Calculate tax and submit to HMRC via integrations service |

## Estimate vs submit

- **`/calculate`** и **`/mtd/prepare`** (read-only): оценка и подготовка тел для MTD **без** отправки в HMRC; доступно согласно продуктовой матрице планов. **`/mtd/prepare`** — единая точка для тех же цифр, что даст submit через integrations после confirm.
- **Submit в HMRC** (в т.ч. через `integrations-service` quarterly): только после **явного подтверждения** пользователя; в проде включайте `HMRC_REQUIRE_EXPLICIT_CONFIRM=true` на `integrations-service`. См. `docs/POLICY_SPEC.md` и `docs/runbooks/HMRC_INTEGRATIONS_ENV.md`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| COMPLIANCE_SERVICE_URL | No | - | When set, successful `POST /calculate` and `POST /calculate-and-submit` emit compliance audit events |
| TRANSACTIONS_SERVICE_URL | No | http://localhost:8002/transactions/me | URL of the transactions service |
| INTEGRATIONS_SERVICE_URL | No | http://localhost:8010/integrations/hmrc/submit-tax-return | URL of the integrations HMRC endpoint |
| CALENDAR_SERVICE_URL | No | http://localhost:8015/events | URL of the calendar service |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
