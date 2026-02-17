# SelfMonitor Mobile App (Expo)

Native shell application for iOS/Android that reuses the existing `apps/web-portal`
experience through `react-native-webview`.

## Why this approach

- fast time-to-market for mobile stores;
- max reuse of already production-ready web functionality;
- native capabilities can be added incrementally (camera, push, secure storage).

## Quick start

```bash
cd apps/mobile
npm install
cp .env.example .env
npm run start
```

## Environment

- `EXPO_PUBLIC_WEB_PORTAL_URL`: URL of deployed web portal or local dev instance.
- `EXPO_PUBLIC_PARTNER_REGISTRY_URL`: partner-registry API URL for mobile calendar reminder sync.
- `EXPO_PUBLIC_EAS_PROJECT_ID`: Expo project ID for stable push token issuance in EAS builds.
- `EXPO_PUBLIC_MOBILE_REMOTE_CONFIG_URL`: optional remote config endpoint for onboarding A/B variants and branded splash content.
- `EXPO_PUBLIC_MOBILE_ANALYTICS_URL`: optional endpoint to receive mobile funnel analytics events.
- `EXPO_PUBLIC_MOBILE_ANALYTICS_API_KEY`: optional API key sent as `X-Api-Key` to analytics endpoint.

Local Android emulator default usually works with:

```env
EXPO_PUBLIC_WEB_PORTAL_URL=http://10.0.2.2:3000
```

For a physical phone, use your machine LAN IP:

```env
EXPO_PUBLIC_WEB_PORTAL_URL=http://<YOUR_LAN_IP>:3000
```

## Available scripts

- `npm run start` - start Expo dev server
- `npm run android` - open Android emulator/device
- `npm run ios` - open iOS simulator/device
- `npm run web` - run Expo web preview
- `npm run typecheck` - TypeScript validation
- `npm run build:android:preview` - cloud build (Android preview)
- `npm run build:ios:preview` - cloud build (iOS preview)
- `npm run build:android:prod` - cloud build (Android production)
- `npm run build:ios:prod` - cloud build (iOS production)

## Current status

Implemented in this iteration:

- WebView container for the existing web-portal;
- Lottie onboarding screen for first-time launch;
- biometric unlock gate (Face ID/Touch ID/device biometrics) for secured sessions;
- push deep-link routing (path/route/url payload support);
- branded splash launch screen with remote-configurable copy and gradient theme;
- onboarding A/B variant assignment (stable by installation ID);
- onboarding and security funnel analytics events (impression/cta/completion/biometric/push/deep-link);
- cinematic command card (live time, connectivity pulse, secure-session state);
- animated neo-dock with premium quick actions and route highlights;
- haptic feedback for key interactions (navigation, scan launch, push setup);
- pull-to-refresh support;
- Android hardware back handling;
- offline banner and error recovery action;
- secure session bootstrap from native secure storage;
- web/native auth bridge (session state sync);
- push-notification permission and token registration shortcut;
- secure calendar reminder sync from partner-registry with local push scheduling and auto-reschedule;
- quick mobile action bar (dashboard/documents/receipt capture/push setup);
- configurable URL via environment variable.

Planned next:

- backend endpoint for push token registration and user mapping;
- in-app notification center with delivery status and action deep-links;
- camera-first receipt capture shortcut with direct upload pipeline;
- dashboard-level BI rollups for onboarding conversion and biometric unlock success.

## App Store / Google Play preparation

1. Install and authenticate EAS CLI:
   ```bash
   npm install -g eas-cli
   eas login
   ```
2. Configure credentials:
   ```bash
   eas credentials
   ```
3. Build artifacts:
   ```bash
   npm run build:android:preview
   npm run build:ios:preview
   ```
