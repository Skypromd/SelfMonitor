# HMRC MTD Direct Submission Runbook

Operational runbook for direct HMRC quarterly submissions, credential hygiene, and fallback safety.

## 1) Required configuration

- `HMRC_DIRECT_SUBMISSION_ENABLED=true`
- `HMRC_OAUTH_TOKEN_URL`
- `HMRC_OAUTH_CLIENT_ID`
- `HMRC_OAUTH_CLIENT_SECRET`
- `HMRC_OAUTH_SCOPE`
- `HMRC_QUARTERLY_ENDPOINT_PATH`
- `HMRC_REQUEST_TIMEOUT_SECONDS`

Resilience and governance:
- `HMRC_DIRECT_FALLBACK_TO_SIMULATION` (recommended `true` in early production hardening)
- `HMRC_OAUTH_CREDENTIALS_ROTATED_AT` (ISO date)
- `HMRC_OAUTH_ROTATION_MAX_AGE_DAYS` (default 90)
- `HMRC_SLO_WINDOW_SIZE`
- `HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT`
- `HMRC_SLO_P95_LATENCY_TARGET_MS`

## 2) Preflight checks

1. `GET /integrations/hmrc/mtd/operational-readiness`
2. Confirm:
   - `oauth_credentials_configured=true`
   - `credential_rotation_overdue=false`
   - readiness band is `ready` or accepted `degraded` with explicit sign-off
3. Validate SLO baseline:
   - `GET /integrations/hmrc/mtd/submission-slo`

## 3) Rotation procedure (OAuth credentials)

1. Rotate credentials in secrets manager.
2. Update runtime environment.
3. Set `HMRC_OAUTH_CREDENTIALS_ROTATED_AT=<today ISO date>`.
4. Deploy `integrations-service`.
5. Verify:
   - operational readiness endpoint,
   - one non-production smoke submission.

## 4) Fallback procedure (direct -> simulation)

Trigger when:
- HMRC upstream is unstable,
- OAuth errors persist,
- p95 latency or success rate SLO breaches.

Steps:
1. Set `HMRC_DIRECT_FALLBACK_TO_SIMULATION=true`.
2. Keep direct mode enabled for observability, but allow automatic safe fallback.
3. Verify submission responses include fallback notice in `message`.
4. Track fallback count via submission SLO endpoint.

## 5) Recovery to normal direct mode

1. Resolve upstream/credential issue.
2. Confirm readiness and SLO recovery.
3. Keep fallback enabled for 24h observation window, then optionally disable.
4. Log timeline and closure in compliance incident record.
