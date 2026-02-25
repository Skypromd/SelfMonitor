# Performance and Load Baseline Snapshot

This document tracks a repeatable baseline for execution speed of critical smoke flows.
It complements SLO monitoring (`docs/observability/SLO_DASHBOARDS.md`) with a concrete
release-gate performance snapshot that can be compared over time.

## Latest baseline (2026-02-16 cycle)

- Snapshot artifact: `docs/observability/baselines/preflight_quick_2026-02-16.json`
- Command used:

```bash
python3 tools/release_preflight.py --quick --include-frontend \
  --timings-json docs/observability/baselines/preflight_quick_2026-02-16.json
```

### Results

| Check ID | Description | Duration (s) | Status |
|---|---|---:|---|
| `auth_login` | Auth login smoke | 1.5629 | pass |
| `transactions_import` | Transactions import smoke | 1.0824 | pass |
| `handoff_audit` | Partner handoff audit smoke | 0.9960 | pass |
| `invoice_exports` | Invoice PDF and accounting CSV smoke | 1.0350 | pass |
| `web_build` | Web portal production build | 4.6923 | pass |
| **total** | **all selected checks** | **9.3686** | **pass** |

## Regression policy

- API smoke checks (`auth_login`, `transactions_import`, `handoff_audit`, `invoice_exports`):
  - investigate if runtime regresses by **>= 30%** against previous baseline.
- Web build (`web_build`):
  - investigate if runtime regresses by **>= 20%** against previous baseline.
- Any failed check remains a hard release blocker regardless of runtime.

## Update cadence

- Refresh baseline:
  - before each production release candidate, and
  - at least once per sprint.
- Keep snapshots under `docs/observability/baselines/` with date suffix.

