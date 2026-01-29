# Mobile App (Expo)

## Overview
React Native (Expo) client for the Self-Assessment platform.

## Requirements
- Node.js 18+
- Expo CLI

## Install
```
cd apps/mobile
npm install
```

## Run
```
npm start
```

## Environment variables
Set these before running (optional):
- `EXPO_PUBLIC_API_GATEWAY_URL` (default: http://localhost:8000/api)
- `EXPO_PUBLIC_LOCALIZATION_SERVICE_URL` (optional override)
- `EXPO_PUBLIC_STRIPE_CHECKOUT_URL` (Stripe Checkout link)
- `EXPO_PUBLIC_STRIPE_CHECKOUT_ANNUAL_URL` (optional annual link)
- `EXPO_PUBLIC_STRIPE_PORTAL_URL` (billing portal link)

## Screens
- Dashboard (Tax Readiness + Cash Flow)
- Transactions (bank connect + CSV)
- Documents (scan/upload)
- Reports (monthly/quarterly/P&L/tax year/mortgage)
- Profile & Subscription
- Marketplace, Settings, Support
