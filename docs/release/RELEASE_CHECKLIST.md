# Release Checklist

Use this checklist for each production release.

Related docs:
- `docs/release/GO_LIVE_RUNBOOK.md`
- `docs/release/ROLLBACK_DRILL.md`

## 1. Pre-release gates

- [ ] CI is green (`python-services`, `web-portal`, `smoke-core-flow`).
- [ ] No critical/high security findings in dependency scan.
- [ ] `python3 tools/release_preflight.py --quick` passes from repo root.
- [ ] Release notes drafted and reviewed.
- [ ] On-call engineer assigned for release window.

## 2. Database and migration safety

- [ ] Confirm migration scripts for changed services exist and are tested in staging.
- [ ] Run forward migrations in staging and validate startup health.
- [ ] Confirm backward compatibility window (if rolling deploy).
- [ ] Backup/restore point created before production migration.

## 3. Deployment plan

- [ ] Define target version/tag for each deployable service.
- [ ] Confirm config/env changes are applied (including secrets and URLs).
- [ ] Roll out in stages (canary or phased deployment).
- [ ] Validate health checks and key endpoints after each stage.

## 4. Rollback plan

- [ ] Document rollback command/steps for each service.
- [ ] Verify previous stable image/tag is available.
- [ ] Define rollback trigger thresholds (error-rate, latency, availability).
- [ ] Confirm data rollback strategy for non-reversible migrations.
- [ ] Rollback drill evidence is current (last 90 days) per `docs/release/ROLLBACK_DRILL.md`.

## 5. Post-release validation

- [ ] Run smoke checks on auth/profile/transactions flow.
- [ ] Validate monetization smoke path:
  - generate invoice snapshot,
  - download PDF invoice,
  - export accounting CSV for `xero` and `quickbooks`.
- [ ] Verify SLO dashboards (availability, error rate, p95 latency).
- [ ] Verify alert channels are active and not noisy.
- [ ] Announce release completion with validation summary.

## 6. Security and compliance

- [ ] Validate secrets are sourced from env/Vault; no hardcoded secrets introduced.
- [ ] Verify auth/JWT checks are active on protected endpoints.
- [ ] Confirm audit events are being produced for security-relevant actions.
- [ ] Ensure dependency updates do not introduce known critical CVEs.
- [ ] Confirm current legal policy version (`AUTH_LEGAL_CURRENT_VERSION`) is published and acceptance endpoint works.
- [ ] Confirm auth runtime durability is enabled in target environment (prefer `AUTH_RUNTIME_STATE_BACKEND=redis` and segmented mode).
- [ ] Confirm auth cleanup policy settings are explicitly set (`AUTH_RUNTIME_CLEANUP_ENABLED`, `AUTH_RUNTIME_CLEANUP_INTERVAL_SECONDS`).
- [ ] Confirm WAF observability dashboards/alerts are active (`docs/observability/WAF_MONITORING_AND_ALERTS.md`).

