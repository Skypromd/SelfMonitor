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
1. Client calls `POST /connections/initiate` with `provider_id: "saltedge"`.
2. Service creates a Salt Edge customer (or reuses existing).
3. Service creates a Connect session and returns `consent_url`.
4. User completes consent in Salt Edge Connect.
5. Salt Edge redirects to your `redirect_uri` with `connection_id`.
6. Client calls `GET /connections/callback?provider_id=saltedge&connection_id=...`.

## Notes
- The current implementation stores provider metadata in Vault.
- Transaction sync is optional and depends on Salt Edge API access.
- If transactions are not returned on callback, schedule a sync job separately.
