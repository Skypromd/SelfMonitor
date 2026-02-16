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

## Current status

Implemented in this iteration:

- WebView container for the existing web-portal;
- pull-to-refresh support;
- Android hardware back handling;
- offline banner and error recovery action;
- configurable URL via environment variable.

Planned next:

- secure token storage with native keychain/keystore;
- push notifications for HMRC deadlines and invoice reminders;
- camera-first receipt capture shortcut with native permissions flow.
