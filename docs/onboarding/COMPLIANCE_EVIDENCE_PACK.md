# Compliance Evidence Pack (Seed Data Room)

Use this pack to provide investor-grade evidence for regulatory reliability and control maturity.

## 1) Regulatory submission controls

- HMRC MTD module spec and validation:
  - `GET /integrations/hmrc/mtd/quarterly-update/spec`
- Direct submission path:
  - `POST /integrations/hmrc/mtd/quarterly-update`
- Operational controls:
  - `GET /integrations/hmrc/mtd/operational-readiness`
  - `GET /integrations/hmrc/mtd/submission-slo`

## 2) Required evidence artifacts

- [ ] HMRC quarterly payload validation examples (pass/fail samples).
- [ ] Last 90-day submission SLO snapshot exports.
- [ ] OAuth credential rotation proof (date, operator, rotation ticket).
- [ ] Fallback-mode validation evidence (direct outage simulation result).
- [ ] Runbook links:
  - `docs/release/GO_LIVE_RUNBOOK.md`
  - `docs/release/HMRC_MTD_DIRECT_RUNBOOK.md`
  - `docs/release/ROLLBACK_DRILL.md`

## 3) Audit and security controls

- [ ] RBAC scope/role model for investor and billing endpoints.
- [ ] Audit event samples:
  - invoice lifecycle updates,
  - NPS submissions,
  - marketing spend ingestion.
- [ ] Cross-user isolation test evidence for agent and metrics flows.

## 4) Incident governance evidence

- [ ] Incident classification matrix filled for last quarter.
- [ ] At least one completed postmortem template:
  - `docs/release/COMPLIANCE_INCIDENT_POSTMORTEM_TEMPLATE.md`
- [ ] Corrective action closure rate with owner and due date.

## 5) Investor-ready output

Package the above into a dated folder:

`/data-room/compliance/YYYY-MM-DD/`

Include:
- API snapshots (JSON/CSV),
- dashboard screenshots,
- signed runbook review note,
- incident/postmortem evidence.
