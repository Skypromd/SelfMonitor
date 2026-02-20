# Client Demo Runbook (10-15 minutes)

**Purpose:** stable, repeatable demo flow for customer presentation.

---

## 1) Preconditions

1. Create runtime env file from template:

```bash
cp .env.example .env
```

2. Fill required values in `.env`:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `AUTH_SECRET_KEY`
- `VAULT_ADDR`, `VAULT_TOKEN`
- `WEAVIATE_API_KEY`, `WEAVIATE_ADMIN_USER`
- `QNA_INTERNAL_TOKEN`

3. Web portal env should contain:

```env
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:8000/api
```

---

## 2) Startup

### Backend

```bash
docker compose up --build
```

### Frontend

```bash
cd apps/web-portal
npm install
npm run build
npm run dev
```

Open: `http://localhost:3000`

---

## 3) Health Sanity Checks

Check gateway:

```bash
curl http://localhost:8000/health
```

Expected: HTTP 200.

---

## 4) Demo Script (recommended order)

1. **Register + Login**  
   Show secure sign-in and JWT-based session.

2. **Profile**  
   Create/update profile and confirm saved data reload.

3. **Transactions**  
   Initiate banking connection, wait import, view categorized transactions.

4. **Dashboard**  
   Show tax estimate, cash-flow forecast, and advice card.

5. **Submission**  
   Run calculate-and-submit, show returned submission ID and confirmation.

6. **Documents + Search**  
   Upload document, then run semantic search.

7. **Marketplace + Handoff**  
   Trigger partner handoff and confirm success message.

8. **Activity Log**  
   Show audit events (consent/handoff/actions) visible only for current user.

---

## 5) Demo Recovery Tips

- If login fails: verify `AUTH_SECRET_KEY` consistency across all services.
- If documents search fails: verify `QNA_INTERNAL_TOKEN` and Weaviate settings.
- If profile/transactions fail: ensure DB is healthy and migrations completed.
- If API calls fail from browser: ensure frontend uses only `NEXT_PUBLIC_API_GATEWAY_URL`.

---

## 6) Go/No-Go for Client Session

Proceed only if:
- all key pages load without 4xx/5xx errors,
- end-to-end flows in section 4 succeed once,
- no active alerts in observability stack.
