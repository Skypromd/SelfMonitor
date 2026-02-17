# Mobile World-Class Execution TODO

Owner: product/engineering  
Goal: finish "store-polish 10/10" and move mobile channel to measurable growth mode.

## 0. Current sprint status

- [x] Premium shell UX (wow visuals, haptics, neo dock)
- [x] Lottie onboarding + biometric unlock + push deep-links
- [x] Branded splash + client-side A/B + client analytics emitters
- [ ] Backend ingestion for mobile analytics funnel
- [ ] Remote-config endpoint hardening and rollout policy
- [ ] Funnel dashboard + weekly operating cadence

## 1. Backend + data (priority P0)

- [ ] Add `POST /mobile/analytics/events` endpoint for ingesting mobile events
- [ ] Add `GET /mobile/analytics/funnel` endpoint for KPI/funnel snapshot
- [ ] Add `GET /mobile/config` endpoint for splash/onboarding remote config payload
- [ ] Add API key guard for analytics ingestion/read (`X-Api-Key`)
- [ ] Add tests for ingest/funnel/config behavior

## 2. Product analytics (priority P0)

- [ ] Track splash impression/dismiss conversion
- [ ] Track onboarding impression/CTA/completion conversion
- [ ] Track biometric gate shown/success/failure ratio
- [ ] Track push prompt/grant ratio
- [ ] Track push deep-link open and cold-start open rate

## 3. Release + operations (priority P1)

- [ ] Add basic dashboard export endpoint for mobile funnel (JSON)
- [ ] Add weekly KPI review checklist entry for mobile conversion
- [ ] Set target thresholds:
  - [ ] onboarding completion >= 65%
  - [ ] biometric success >= 80%
  - [ ] push opt-in >= 45%
- [ ] Define rollback toggle for onboarding experiment variants

## 4. Store readiness (priority P1)

- [ ] Prepare branded screenshots + app preview video
- [ ] Finalize privacy/deletion wording for app submission metadata
- [ ] Validate TestFlight + Google Internal test scripts
- [ ] Define go-live gate based on 7-day crash-free and funnel thresholds

