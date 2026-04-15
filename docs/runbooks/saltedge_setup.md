# Salt Edge Setup (UK Open Banking)

## Overview
This runbook describes how to configure the Banking Connector service to use Salt Edge.

## Required environment variables
Set the following variables for the `banking-connector` service:

```
SALTEDGE_BASE_URL=https://www.saltedge.com/api/v5
SALTEDGE_APP_ID=your_saltedge_app_id
SALTEDGE_SECRET=your_saltedge_secret
SALTEDGE_CUSTOMER_PREFIX=selfmonitor
SALTEDGE_SCOPES=accounts,transactions
```

> For testing, use Salt Edge sandbox credentials and the sandbox base URL.

## Flow summary
1. Set `BANKING_OPEN_BANKING_PROVIDER=saltedge` (default in `.env.example`) or send `provider_id: "saltedge"` on `POST /connections/initiate`.
2. Service creates a Salt Edge customer (or reuses existing).
3. Service creates a Connect session and returns `consent_url`.
4. User completes consent in Salt Edge Connect.
5. Salt Edge redirects to your `return_to` / `redirect_uri` with `connection_id` (query).
6. Web portal `GET /connections/callback?connection_id=...` (with user JWT) completes import; or call `GET /api/banking/connections/callback?connection_id=...` with `Authorization: Bearer`.
7. Response `connection_id` is the internal UUID stored in Vault; Salt Edge’s connection id is kept under `saltedge_connection_id` in the secret.

## Notes
- The current implementation stores provider metadata in Vault.
- Transaction sync is optional and depends on Salt Edge API access.
- If transactions are not returned on callback, schedule a sync job separately.
- **Mobile (Expo):** register the same `return_to` URL in Salt Edge as the app scheme redirect, e.g. `selfmonitor://banking-callback` (see `apps/mobile/lib/bankingOAuth.ts` — `Linking.createURL` with scheme `selfmonitor` from `app.json`).
