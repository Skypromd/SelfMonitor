# Seed 10/10 Execution TODO

Objective: move project from strong seed-ready to 10/10 investor readiness by proving growth, unit economics, and regulatory reliability with measurable KPI gates.

Status legend:
- [ ] pending
- [x] completed

## Phase S0 — Setup and control plane
- [x] Create and publish this execution TODO in repository.
- [x] Define single source of truth KPI endpoint(s) for investor metrics.
- [ ] Add weekly KPI review cadence and owner checklist.

## Phase S1 — PMF evidence (product-market fit)
- [x] Track activation funnel: signup -> first data import -> first tax-ready period.
- [x] Track 30/60/90-day retention cohorts for active and paying users.
- [x] Add in-product NPS collection and monthly trend reporting.
- [x] Define PMF gate: activation > 60%, 90-day paying retention > 75%, NPS > 45.

## Phase S2 — Revenue and unit economics
- [ ] Add MRR stability dashboard (current MRR, 3-month average, MoM growth).
- [ ] Add churn and expansion metrics for paid plans.
- [ ] Add CAC/LTV placeholders and ingestion contract for marketing spend.
- [ ] Define seed gate: MRR > 40k GBP, churn < 3% monthly, LTV/CAC >= 4.

## Phase S3 — Regulatory moat and reliability
- [ ] Harden HMRC direct submission runbook (OAuth credentials rotation and fallback).
- [ ] Add submission SLO dashboard and alert thresholds (success rate, latency, retries).
- [ ] Add incident classification and postmortem template for compliance-critical paths.

## Phase S4 — Investor data room readiness
- [ ] Build one-click investor snapshot export (KPI + growth + risk controls).
- [ ] Produce compliance evidence pack (audit trail, access controls, rollback proof).
- [ ] Produce GTM evidence pack (channel performance, conversion by segment).

## Current sprint execution
- [x] S0.2 Implement investor KPI source endpoint (`/investor/seed-readiness`) in partner-registry.
- [x] S0.3 Add automated tests and OpenAPI coverage for the endpoint.
- [x] S0.4 Wire endpoint into execution list and mark first run complete.
- [x] S1.1 Implement PMF evidence endpoint (`/investor/pmf-evidence`) with activation and 30/60/90 retention cohorts.
- [x] S1.2 Add tests and OpenAPI contract for PMF evidence snapshot.
- [x] S1.3 Implement NPS submission endpoint (`/investor/nps/responses`) and monthly trend endpoint (`/investor/nps/trend`).
- [x] S1.4 Add dashboard PMF/NPS signals panel with in-product NPS submission form.
- [x] S1.5 Add automated PMF gate endpoint (`/investor/pmf-gate`) with threshold checks and dashboard status indicator.
