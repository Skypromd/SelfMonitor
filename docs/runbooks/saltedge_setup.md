# Salt Edge Setup (UK Open Banking)

## Overview
Runbook for configuring **banking-connector** with **Salt Edge** as the primary Open Banking provider (UK). Bank choice happens **inside Salt Edge Connect** after the user starts the flow from your app.

## Checklist (first-time)

1. **Salt Edge account** — register at [saltedge.com](https://www.saltedge.com), create an application, obtain **App ID** and **Secret** (Pending/Test for fake banks; Test/Live when ready for real ASPSPs).
2. **Redirect URL** — in Salt Edge client settings, allow the same URL you send as `return_to`:
   - Web dev: `http://localhost:3000/connect-bank/callback` (or your real origin + `/connect-bank/callback`).
   - Must match `BANKING_OAUTH_REDIRECT_URI` in root `.env` if you rely on the default documented there.
3. **Compose / env** — set variables for `banking-connector` (see below); restart the service.
4. **Vault** — banking-connector stores tokens/metadata in Vault; ensure `BANKING_VAULT_*` is valid in your environment (see root `.env.example`).
5. **Smoke test** — use a **fake provider** in Salt Edge (e.g. Fake Bank) to complete Connect without a real UK bank; confirm callback hits `/connect-bank/callback?connection_id=...` and transactions or connection appears as expected.

## Required environment variables

```
SALTEDGE_BASE_URL=https://www.saltedge.com/api/v5
SALTEDGE_APP_ID=your_saltedge_app_id
SALTEDGE_SECRET=your_saltedge_secret
SALTEDGE_CUSTOMER_PREFIX=mynettax
SALTEDGE_SCOPES=accounts,transactions
BANKING_OPEN_BANKING_PROVIDER=saltedge
```

Use the sandbox/base URL Salt Edge gives you if it differs from production.

## Flow summary

1. Set `BANKING_OPEN_BANKING_PROVIDER=saltedge` (default in `.env.example`) or send `provider_id: "saltedge"` on `POST /connections/initiate`.
2. Service creates a Salt Edge customer (or reuses existing).
3. Service creates a Connect session and returns `consent_url` (`connect_url`).
4. User completes consent in **Salt Edge Connect** (selects bank there).
5. Salt Edge redirects to `return_to` / `redirect_uri` with `connection_id` (query).
6. Web: `GET /connections/callback?connection_id=...` with user JWT completes the flow (`apps/web-portal/pages/connect-bank/callback.tsx`).
7. Internal `connection_id` is stored in Vault; Salt Edge’s connection id is kept under `saltedge_connection_id` in the secret.

## Web portal

- `NEXT_PUBLIC_OPEN_BANKING_PROVIDER=saltedge` in `apps/web-portal/.env.local` — marks Salt Edge as **Recommended** on `/connect-bank`.
- `NEXT_PUBLIC_BANKING_SERVICE_URL=/api/banking` — same-origin proxy to the gateway.

## Mobile (Expo)

Register the app redirect in Salt Edge (same `return_to` you pass from the app), e.g. `selfmonitor://banking-callback` — see `apps/mobile/lib/bankingOAuth.ts` and `app.json` scheme.

## Notes

- Transaction fetch on callback uses a **90-day** window where applicable (see banking-connector).
- **No background auto-sync** — user must trigger sync per product rules (`AGENTS.md`).
- Trial limits (e.g. active connections) are defined by Salt Edge for Pending/Test accounts; keep a small number of test connections.
