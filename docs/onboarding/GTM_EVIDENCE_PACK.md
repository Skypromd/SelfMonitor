# GTM Evidence Pack (Seed Data Room)

This pack captures go-to-market proof required for investor diligence.

## 1) Core KPIs to include

- Top-of-funnel and conversion:
  - leads_last_90d
  - qualification_rate_percent
  - conversion_rate_percent
- PMF indicators:
  - activation_rate_percent
  - retention_rate_30d_percent / 60d / 90d
  - overall_nps_score
- Unit economics:
  - current_month_mrr_gbp
  - monthly_churn_rate_percent
  - ltv_cac_ratio
  - seed_gate_passed

## 2) Data sources

- `GET /investor/seed-readiness`
- `GET /investor/pmf-evidence`
- `GET /investor/nps/trend`
- `GET /investor/unit-economics`
- `GET /investor/snapshot/export?format=csv`

## 3) Required channel evidence

- [ ] Monthly spend by channel (`/investor/marketing-spend` records).
- [ ] Customer acquisition by channel and month.
- [ ] CAC trend by channel (at minimum: paid search, referrals, affiliates).
- [ ] Funnel conversion trend by month and segment.

## 4) Segment evidence

- [ ] UK self-employed baseline segment metrics.
- [ ] High-intent segment conversion (tax submission intent users).
- [ ] Mortgage-readiness segment engagement and conversion.
- [ ] Retention split by language cohort where available.

## 5) Investor-ready output

Package the above into a dated folder:

`/data-room/gtm/YYYY-MM-DD/`

Include:
- snapshot CSV + JSON,
- channel tables,
- 3-month commentary on experiments and learnings,
- next quarter GTM hypotheses and owners.
