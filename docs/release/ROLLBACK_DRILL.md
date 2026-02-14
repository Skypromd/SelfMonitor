# Rollback Drill Playbook

Use this playbook to practice rollback readiness and during real incidents.

## 1. Drill objective

Prove that the team can safely revert to the previous stable release within the target recovery window.

## 2. Trigger thresholds

Start rollback preparation if any condition persists for 5 minutes:

- 5xx error rate > 2% on critical APIs.
- p95 latency degrades by > 50% versus baseline.
- Billing/admin monetization endpoints become unavailable.

Rollback immediately when:

- Data integrity is at risk.
- Login/authentication is failing for production users.
- Invoice generation or status transitions break business-critical operations.

## 3. Drill cadence

- Perform rollback drill at least once per quarter.
- Perform additional drill after major migration changes.

## 4. Rollback procedure

1. **Declare incident mode**
   - Assign incident commander.
   - Freeze additional deployments.

2. **Pin rollback target**
   - Identify last known good release tag/image for each changed service.
   - Confirm image availability before rollback command execution.

3. **Apply feature-flag safe rollback (first response)**
   - Disable agent writes by setting `AGENT_WRITE_ACTIONS_ENABLED=false`.
   - Redeploy only `agent-service` and validate read-only mode.

4. **Roll back application services**
   - Roll back backend services first (auth, transactions, partner-registry, related dependencies).
   - Roll back frontend/web portal after backend stabilization.

5. **Migration decision**
   - If migrations are backward compatible, keep schema and revert app versions.
   - If migration is non-reversible, apply a forward-fix strategy and do not perform destructive rollback.

6. **Post-rollback verification**
   - Run quick preflight:
     ```bash
     python3 tools/release_preflight.py --quick
     ```
   - Confirm:
     - login flow works,
     - core transaction flow works,
     - invoice generation/export endpoints are healthy.

7. **Close incident**
   - Record timeline and root cause.
   - Capture corrective actions with owners and due dates.

## 5. Drill evidence checklist

- [ ] Start and end timestamps captured.
- [ ] Trigger metric snapshots attached.
- [ ] Rollback commands and target versions documented.
- [ ] Validation results attached.
- [ ] Follow-up actions tracked.
