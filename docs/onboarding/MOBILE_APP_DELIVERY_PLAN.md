# Mobile App Delivery Plan (Native Distribution)

## Objective

Make mobile the primary user channel while reusing the mature web product.

## Chosen implementation path

1. **Phase 1 (current): Expo + WebView shell**
   - wrap existing `apps/web-portal` in native iOS/Android app;
   - ship fast to TestFlight / Google Internal Testing;
   - collect UX and reliability telemetry.
2. **Phase 2: Native capability layer**
   - secure token storage (keychain/keystore);
   - push notifications for HMRC deadlines and reminders;
   - camera shortcut for receipt capture.
3. **Phase 3: Native-first critical flows**
   - receipt capture + OCR review;
   - invoice reminders and payment status;
   - filing deadline and submission status center.

## Delivered in this iteration

- Mobile app scaffold under `apps/mobile`;
- production-ready Expo configuration (`app.json`, Babel, TS config);
- WebView host with:
  - pull-to-refresh,
  - Android hardware back navigation,
  - offline banner and retry flow,
  - env-configurable web URL (`EXPO_PUBLIC_WEB_PORTAL_URL`);
- CI typecheck lane for mobile app.

## Release readiness checklist (next)

- Add bundle identifiers and signing credentials for staging/prod;
- Integrate crash analytics (Sentry/Firebase);
- Enable push provider and notification permissions flow;
- Validate app store metadata and privacy declarations.
