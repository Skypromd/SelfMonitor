# Weekly KPI Review Cadence (Investor Control Plane)

This checklist standardizes weekly KPI governance for seed-readiness and 10/10 execution.

## 1) Meeting cadence and owners

- Cadence: every Monday, 09:30 UK time.
- Duration: 45 minutes.
- Required owners:
  - Product lead (chair, decision owner)
  - Growth lead (funnel, CAC, channel mix)
  - Finance owner (MRR quality, collections, unit economics)
  - Compliance/on-call owner (HMRC reliability, incidents, controls)
  - Engineering owner (delivery status, technical risk)

## 2) KPI source of truth

- KPI APIs:
  - `GET /investor/seed-readiness`
  - `GET /investor/pmf-evidence`
  - `GET /investor/nps/trend`
  - `GET /investor/pmf-gate`
  - `GET /investor/unit-economics`
  - `GET /investor/snapshot/export?format=json`
- HMRC reliability APIs:
  - `GET /integrations/hmrc/mtd/submission-slo`
  - `GET /integrations/hmrc/mtd/operational-readiness`
- Mobile product ops APIs:
  - `GET /mobile/analytics/funnel?days=14`
  - `GET /mobile/analytics/funnel/export?format=csv`
  - `POST /mobile/analytics/weekly-snapshot?days=7`
  - `GET /mobile/analytics/weekly-snapshots?limit=12`
  - `GET /mobile/analytics/weekly-cadence?days=7`
  - `GET /mobile/config`

## 3) Weekly agenda

1. PMF gate status (activation / 90d retention / NPS / sample size).
2. Seed financial gate status (MRR / churn / LTV:CAC).
3. HMRC operational readiness and SLO trend.
4. Mobile funnel trend (splash -> onboarding -> biometric -> push opt-in).
5. Open risks, incidents, and mitigation owner assignment.
6. Investor data-room updates (compliance and GTM evidence deltas).

## 4) Owner checklist (must be completed every week)

- [ ] Product lead confirms PMF gate status and top 3 product actions.
- [ ] Growth lead confirms CAC inputs were ingested for the current month.
- [ ] Finance owner confirms invoice quality and collection trend.
- [ ] Compliance owner confirms HMRC credential rotation state and fallback posture.
- [ ] Engineering owner confirms alert status and release risk summary.
- [ ] Snapshot export attached to weekly record (`/investor/snapshot/export`).
- [ ] Mobile owner confirms weekly snapshot was captured (`POST /mobile/analytics/weekly-snapshot`).
- [ ] Mobile KPI export attached (`/mobile/analytics/funnel/export?format=csv`).
- [ ] A/B onboarding variant summary reviewed (`/mobile/analytics/weekly-cadence`).

## 5) Exit criteria for the weekly review

- Every failed gate criterion has one owner and due date.
- Every critical reliability risk has mitigation and rollback plan.
- KPI deltas and decisions are logged in the weekly operating notes.
