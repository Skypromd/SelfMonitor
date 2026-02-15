# Compliance-Critical Incident Postmortem Template

Use for incidents affecting HMRC submissions, tax integrity, access control, or auditability.

## 1) Incident metadata

- Incident ID:
- Start time (UTC):
- End time (UTC):
- Severity: (SEV-1 / SEV-2 / SEV-3)
- Detection source: (alert, manual, support, partner)
- Incident commander:
- Compliance owner:

## 2) Classification

- Category:
  - [ ] HMRC direct submission outage
  - [ ] OAuth credential / auth failure
  - [ ] Submission data validation defect
  - [ ] Access control or data isolation concern
  - [ ] Audit trail / evidence gap
  - [ ] Other (specify)
- Compliance impact:
  - [ ] Regulatory submission delay risk
  - [ ] Potential incorrect filing risk
  - [ ] Data protection risk
  - [ ] No direct external impact

## 3) Impact assessment

- Affected users/tenants:
- Affected endpoints/services:
- Approximate failed/impacted submissions:
- Business impact summary:

## 4) Timeline

- T0 detection:
- T+ mitigation:
- T+ rollback/fallback:
- T+ service restored:
- T+ final verification:

## 5) Root cause

- Technical root cause:
- Process root cause:
- Why existing controls did not prevent it:

## 6) Containment and recovery

- Immediate actions taken:
- Fallback used (`direct->simulation`): yes/no
- Data integrity verification completed: yes/no
- Residual risk after recovery:

## 7) Corrective and preventive actions

| Action | Owner | Due date | Status |
|---|---|---|---|
|  |  |  |  |

## 8) Evidence attachments

- Submission SLO snapshot(s)
- Operational readiness snapshot
- Relevant logs/traces
- Customer/compliance communication
