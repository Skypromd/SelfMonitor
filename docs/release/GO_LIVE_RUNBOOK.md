# Go-Live Runbook

This runbook is used for production go-live and patch releases.

## 1. Scope and owners

- Release commander: owns execution timeline.
- On-call engineer: owns alerts and rollback decision.
- Backend owner: validates API and migrations.
- Frontend owner: validates admin/web portal critical paths.

## 2. Preconditions

- CI is green (`python-services`, `web-portal`, `smoke-core-flow`).
- No unresolved critical incidents in current environment.
- Release notes are finalized and approved.
- A rollback target (previous stable image/tag) is available for every changed service.

## 3. Preflight checks (T-30 minutes)

From repository root:

```bash
python3 tools/release_preflight.py --quick
```

Recommended full preflight before major releases:

```bash
python3 tools/release_preflight.py --include-frontend
```

## 4. Deployment sequence

1. Freeze feature merges to `main` during rollout window.
2. Capture backup/restore point for production databases.
3. Apply migrations for changed services (partner-registry included).
4. Deploy backend services in controlled waves.
5. Deploy web portal after backend API health is confirmed.
6. Monitor logs and SLO dashboards for at least 15 minutes before widening traffic.

## 5. Post-deploy monetization verification

Use admin console and/or API checks to verify:

1. Lead lifecycle updates still work (`initiated -> qualified -> converted/rejected`).
2. Billing report loads for selected date range and statuses.
3. Invoice generation returns expected fields:
   - `invoice_number` format: `INV-YYYYMM-######`
   - `due_date` present and valid
4. Invoice artifacts are downloadable:
   - PDF export (`/billing/invoices/{id}/pdf`)
   - Accounting CSV (`target=xero`, `target=quickbooks`)

## 6. Success criteria

- No elevated 5xx rate compared to pre-release baseline.
- p95 latency remains within SLO thresholds.
- No auth or RBAC regression for protected monetization endpoints.
- Finance operations can generate at least one invoice and download both CSV mappings.

## 7. Exit and handover

- Announce release completion with validation summary.
- Keep heightened monitoring for at least one hour.
- Record issues and follow-up actions in release notes.
