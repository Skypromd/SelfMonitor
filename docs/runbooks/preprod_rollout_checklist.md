# Pre-Production Checklist and Rollout Plan

**Date:** 2026-02-19  
**Baseline commit:** `0cab782`  
**Scope:** monorepo services + web portal

---

## 1) Pre-Prod Readiness Checklist

Use this list as strict **go/no-go** gates before production rollout.

### 1.1 Configuration and Secrets

- [ ] `.env` values are set from a secret manager (not defaults from `.env.example`).
- [ ] `AUTH_SECRET_KEY` is identical for all JWT-validating services.
- [ ] `VAULT_ADDR` and `VAULT_TOKEN` are valid for target environment.
- [ ] `WEAVIATE_API_KEY`, `WEAVIATE_ADMIN_USER`, `QNA_INTERNAL_TOKEN` are set and rotated.
- [ ] DB credentials (`POSTGRES_*`) are environment-specific and strong.

### 1.2 Database and Storage

- [ ] PostgreSQL is reachable and backups are verified.
- [ ] Persistent volumes exist and are mounted:
  - `auth_data`
  - `consent_data`
  - `analytics_data`
  - `calendar_data`
  - `partner_registry_data`
  - `integrations_data`
- [ ] Migration commands complete cleanly:
  - `user-profile-service`
  - `transactions-service`
  - `compliance-service`
  - `documents-service`

### 1.3 CI/CD and Test Gates

- [ ] GitHub Actions workflow `Monorepo CI` is green on the target commit.
- [ ] Python service matrix checks are green.
- [ ] Web portal build is green.
- [ ] Contract/integration tests (if enabled for target env) are green.

### 1.4 Security and Access Control

- [ ] Internal-only APIs are not publicly routed by API gateway:
  - `/api/calendar/*`
  - `/api/categorization/*`
  - `/api/integrations/*`
- [ ] Cross-service auth propagation is confirmed:
  - consent -> compliance
  - partner-registry -> compliance
  - tax-engine -> calendar + integrations
  - transactions -> categorization
  - documents worker -> qna (`X-Internal-Token`)
- [ ] Weaviate anonymous access is disabled.
- [ ] `/health` endpoints respond for all services.

### 1.5 Observability and Operations

- [ ] Prometheus targets are up.
- [ ] Grafana dashboards load and show live data.
- [ ] Loki/Promtail pipeline receives logs.
- [ ] Jaeger traces are visible for core flows.
- [ ] Alert channels are configured (Pager/Slack/email).

### 1.6 Business Smoke Scenarios (must pass)

- [ ] User register/login/profile update.
- [ ] Banking callback -> async import -> transaction list/category update.
- [ ] Tax calculate and submit flow.
- [ ] Documents upload -> OCR worker -> semantic search.
- [ ] Consent grant/revoke and activity log visibility.
- [ ] Partner handoff + handoff history visibility.

---

## 2) Rollout Plan (Staging -> Canary -> Full Prod)

### Stage A: Staging Promotion

1. Deploy target commit to staging.
2. Run automated smoke suite.
3. Run manual smoke scenarios from section 1.6.
4. Soak for at least 30-60 minutes under synthetic traffic.

**Exit criteria:** no P0/P1 defects, no sustained error spike, no failed healthchecks.

### Stage B: Canary (5-10% traffic)

1. Route 5-10% user traffic to new version.
2. Observe for 30 minutes:
   - error rate
   - p95/p99 latency
   - auth failures
   - worker queue lag
3. Compare against baseline.

**Stop criteria (immediate rollback):**
- 5xx > baseline by >2x for 5+ minutes
- authentication failures >2%
- queue lag continuously rising
- data corruption indicators / failed writes

### Stage C: Progressive Ramp

1. Increase to 25%.
2. Increase to 50%.
3. Increase to 100%.

Hold 15-30 minutes between steps and check all SLOs each step.

### Stage D: Post-Deploy Verification

1. Re-run smoke flows.
2. Verify dashboard/alerts noise is normal.
3. Confirm no backlog in async workers.
4. Mark release as stable.

---

## 3) Rollback Runbook

### 3.1 Rollback Triggers

- Any P0 incident (auth outage, data loss risk, sustained 5xx spike).
- Security misconfiguration or secret leak detection.

### 3.2 Rollback Steps

1. Shift traffic to previous stable release.
2. Confirm healthchecks on previous release.
3. Validate core user journeys.
4. Disable problematic canary artifacts.
5. Open incident ticket with timestamps and metrics snapshot.

### 3.3 Data Safety Notes

- Do not run destructive schema changes without verified backup/restore.
- If partial writes occurred, execute service-specific reconciliation scripts before re-rollout.

---

## 4) Ownership Matrix (fill before release)

- Release manager: `TBD`
- Backend on-call: `TBD`
- Frontend on-call: `TBD`
- Infra/SRE on-call: `TBD`
- Security approver: `TBD`

---

## 5) Final Go/No-Go Decision

Release is **GO** only if all required boxes are checked and there are no open P0/P1 items.
