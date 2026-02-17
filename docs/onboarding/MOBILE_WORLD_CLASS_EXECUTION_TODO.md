# Mobile World-Class Execution TODO

Owner: product/engineering  
Goal: finish "store-polish 10/10" and move mobile channel to measurable growth mode.

## 0. Current sprint status

- [x] Premium shell UX (wow visuals, haptics, neo dock)
- [x] Lottie onboarding + biometric unlock + push deep-links
- [x] Branded splash + client-side A/B + client analytics emitters
- [x] Backend ingestion for mobile analytics funnel
- [x] Remote-config endpoint hardening and rollout policy
- [x] Funnel dashboard + weekly operating cadence

## 1. Backend + data (priority P0)

- [x] Add `POST /mobile/analytics/events` endpoint for ingesting mobile events
- [x] Add `GET /mobile/analytics/funnel` endpoint for KPI/funnel snapshot
- [x] Add `GET /mobile/config` endpoint for splash/onboarding remote config payload
- [x] Add API key guard for analytics ingestion/read (`X-Api-Key`)
- [x] Add tests for ingest/funnel/config behavior

## 2. Product analytics (priority P0)

- [x] Track splash impression/dismiss conversion
- [x] Track onboarding impression/CTA/completion conversion
- [x] Track biometric gate shown/success/failure ratio
- [x] Track push prompt/grant ratio
- [x] Track push deep-link open and cold-start open rate

## 3. Release + operations (priority P1)

- [x] Add basic dashboard export endpoint for mobile funnel (JSON)
- [x] Add weekly KPI review checklist entry for mobile conversion
- [ ] Set target thresholds:
  - [x] onboarding completion >= 65%
  - [x] biometric success >= 80%
  - [x] push opt-in >= 45%
- [x] Define rollback toggle for onboarding experiment variants

## 4. Store readiness (priority P1)

- [ ] Prepare branded screenshots + app preview video
- [ ] Finalize privacy/deletion wording for app submission metadata
- [ ] Validate TestFlight + Google Internal test scripts
- [x] Define go-live gate based on 7-day crash-free and funnel thresholds

