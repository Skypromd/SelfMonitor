# SelfMonitor — Tax & Finance Platform for UK Self-Employed

All-in-one mobile-first platform for self-employed individuals in the UK. MTD tax filing, invoicing, mortgage readiness, AI advisor — in 10 languages.

## What It Does

| Feature | Description |
|---|---|
| **MTD Tax Filing** | Quarterly updates + final declaration directly to HMRC |
| **Tax Calculators** | PAYE, self-employed, rental, CIS, dividend, crypto |
| **Invoicing** | Create, send, auto-chase, recurring, payment links, PDF generation |
| **Mortgage Advisor** | Readiness score, affordability calculator, stamp duty, lender matching (8 UK banks) |
| **Bank Sync** | Connect bank accounts, sync transactions by button press (no auto-sync) |
| **Receipt Scanner** | Camera → OCR → auto-create transaction |
| **AI Assistant** | Multilingual tax & mortgage advice with voice input |
| **10 Languages** | EN, PL, RO, UA, RU, ES, IT, PT, TR, BN |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Clients                            │
│  📱 Mobile (Expo/RN)    🌐 Web (Next.js)             │
└──────────────┬──────────────────┬────────────────────┘
               │                  │
               ▼                  ▼
        ┌──────────────────────────────┐
        │   nginx gateway (:8000)       │
        └──────────────┬───────────────┘
                       │
    ┌──────────────────┼──────────────────────┐
    │                  │                      │
    ▼                  ▼                      ▼
 33 Python          PostgreSQL            Redis
 microservices      (master)              (cache/queue)
 (FastAPI)
```

### Backend Services (33 containers)

| Category | Services |
|---|---|
| **Core** | auth, user-profile, transactions, compliance, consent |
| **Finance** | tax-engine (7 calculators), invoice-service, billing (Stripe), banking-connector |
| **HMRC** | integrations-service (13 MTD endpoints), mtd-agent (MTD workflow: **prepare → user confirms → submit** — never unattended submission), finops-monitor |
| **Mortgage** | analytics-service (12 mortgage endpoints + lender DB) |
| **AI** | ai-agent-service, voice-gateway (STT/TTS), support-ai |
| **Data** | categorization (200+ UK merchants), documents (OCR), calendar, localization |
| **Growth** | referral-service, cost-optimization, partner-registry |
| **Infra** | postgres, redis, vault, localstack (S3), weaviate, jaeger |

### Frontend

| App | Tech | Screens |
|---|---|---|
| **Mobile** | Expo SDK 51 / React Native 0.74.5 | 14 screens, Revolut-style dark UI |
| **Web Portal** | Next.js 13 | 28 pages |

## HMRC MTD Integration

Sandbox tested and approved. All minimum functionality requirements met:

| Requirement | Status |
|---|---|
| Fraud prevention headers | ✅ Validated by HMRC |
| Business details | ✅ Tested |
| Obligations (deadlines) | ✅ Tested |
| Quarterly periodic updates | ✅ Submitted to sandbox |
| Tax calculation estimate | ✅ Working |
| Final declaration | ✅ Working |
| Loss adjustments | ✅ Working |
| BSAS | ✅ Working |
| VAT return | ✅ Working |

HMRC Sandbox App ID: `04c10afd-a1bd-4328-b993-27169719e9a1`

## Quick Start

### 1. Backend (Docker Compose)

```bash
cp .env.example .env
# Edit .env — see comments for Stripe, HMRC, Open Banking setup
docker compose up --build -d
```

API gateway: `http://localhost:8000`

**Все сервисы из compose + GraphQL gateway** (включая профиль `graphql`):

```bash
docker compose --profile graphql up --build -d
```

Подробнее: `docs/runbooks/FULL_STACK_DOCKER.md` или `scripts/run_full_stack.ps1` (Windows).

### 2. Web Portal

```bash
cd apps/web-portal
npm install
cp .env.example .env.local   # optional: edit .env.local for practolog / prod URLs
npm run dev
```

Web portal: `http://localhost:3000`

#### Deploy: web portal ↔ API gateway

| Topic | What to do |
|--------|------------|
| **Env** | Copy `apps/web-portal/.env.local` from comments in repo or create it. Use **same-origin** API paths (`NEXT_PUBLIC_API_GATEWAY_URL=/api`, `NEXT_PUBLIC_AUTH_SERVICE_URL=/api/auth`, etc.) so the browser calls `http://localhost:3000/api/...` and Next.js **rewrites** proxy to the gateway (see `apps/web-portal/next.config.js`). Avoid `http://localhost:8000` in `NEXT_PUBLIC_*` for the browser unless nginx CORS is fully configured for every route you use. |
| **Backend** | Gateway: `http://localhost:8000`. Typical local backend: `scripts/start_backend_v1.ps1` / `scripts/start_backend_v1.sh` or `docker compose` + `nginx-gateway`. |
| **nginx** | After editing `nginx/nginx.conf` or `nginx/snippets/*`, rebuild/restart: `docker compose up -d --build nginx-gateway`. Snippet `nginx/snippets/cors_api_gateway.conf` adds CORS for preflight when clients hit **:8000** directly (e.g. mobile). |
| **v1 slice** | Lean stack: `scripts/compose_v1_up.ps1` / `.sh` — includes `partner-registry` for `/api/partners`. |
| **Operator subdomain `practolog`** | Optional: separate **origin** for operators (different `sessionStorage` from end users). Enable in `apps/web-portal/.env.local`: `NEXT_PUBLIC_ADMIN_SUBDOMAIN_ENABLED=1`, `NEXT_PUBLIC_ADMIN_HOST=practolog.localhost`, `NEXT_PUBLIC_CLIENT_ORIGIN=http://localhost:3000`, `NEXT_PUBLIC_ADMIN_ORIGIN=http://practolog.localhost:3000`. Then open **`http://practolog.localhost:3000`** for `/admin`, `/admin/login`, Platform billing (`/billing`). Clients use **`http://localhost:3000`**. Logic: `apps/web-portal/middleware.ts`, helpers: `apps/web-portal/lib/adminSurface.ts`. **Production:** DNS + TLS for e.g. `practolog.example.com` and `app.example.com`; set the four variables to HTTPS origins. |
| **Admin account** | Not created via `/register`. Use auth bootstrap (`AUTH_BOOTSTRAP_ADMIN`, `AUTH_ADMIN_EMAIL`, `AUTH_ADMIN_PASSWORD` in root `.env`) and **`/admin/login`** (on practolog host when subdomain mode is on). |
| **Build** | `cd apps/web-portal && npm run build` (CI parity). |

Further production checklists: `docs/TODO_PRODUCTION.md`, `docs/COMPOSE_PRODUCTION.md`, `docs/GO_LIVE_CHECKLIST.md`.

### 3. Mobile App

```bash
cd apps/mobile
npm install
npx expo start
```

Scan QR with Expo Go on your phone.

## Mobile App (14 screens)

| Tab | Screen | Feature |
|---|---|---|
| 🏠 Home | Dashboard | Hero balance, tax status, quick actions, recent transactions |
| 📸 Scan | Receipt Scanner | Camera → OCR → transaction |
| 🔄 Sync | Bank Sync | Connect bank, sync button with daily limit per subscription tier |
| 🤖 AI | Assistant | Chat with AI, voice input, tax & mortgage advice |
| ⋯ More | Profile, Reports, Invoices, Mortgage, Activity | Full feature access |

## API Endpoints (highlights)

### HMRC MTD (13 endpoints)
```
POST /api/integrations/integrations/hmrc/mtd/periodic-update
POST /api/integrations/integrations/hmrc/mtd/final-declaration
POST /api/integrations/integrations/hmrc/mtd/tax-calculation
POST /api/integrations/integrations/hmrc/mtd/loss-adjustment
POST /api/integrations/integrations/hmrc/vat/return
GET  /api/integrations/integrations/hmrc/mtd/business-details
GET  /api/integrations/integrations/hmrc/mtd/obligations
GET  /api/integrations/integrations/hmrc/mtd/bsas/{tax_year}
GET  /api/integrations/integrations/hmrc/mtd/operational-readiness
```

### Tax Calculators (5 endpoints)
```
POST /api/tax/calculators/paye
POST /api/tax/calculators/rental
POST /api/tax/calculators/cis
POST /api/tax/calculators/dividend
POST /api/tax/calculators/crypto
```

### Mortgage (12 endpoints)
```
POST /api/analytics/mortgage/readiness
POST /api/analytics/mortgage/affordability
POST /api/analytics/mortgage/stamp-duty
POST /api/analytics/mortgage/lender-match
POST /api/analytics/mortgage/checklist
POST /api/analytics/mortgage/pack-index
POST /api/analytics/mortgage/pack-index.pdf
GET  /api/analytics/mortgage/types
GET  /api/analytics/mortgage/lender-profiles
```

### Invoicing (10+ endpoints)
```
POST /api/billing/invoices
POST /api/billing/invoices/{id}/chase
POST /api/billing/invoices/{id}/payment-link
POST /api/billing/invoices/recurring
GET  /api/billing/invoices/overdue/list
```

### Categorization (200+ UK merchants)
```
POST /api/categorization/categorize
POST /api/categorization/categorize/bulk
GET  /api/categorization/categories
```

## Subscription Tiers

| Tier | Price | Bank Sync | Key Features |
|---|---|---|---|
| Free | £0 | No sync | Manual entry, dashboard, tax calculator |
| Starter | £12/mo | 1×/day | CIS tracker, guided MTD, 1 bank |
| Growth | £15/mo | 3×/day | 2 banks, 12 mo history, guided MTD |
| Pro | £18/mo | 10×/day | 5 banks, direct+fraud MTD, VAT, 24 mo history |
| Business | £28/mo | 25×/day | 10 banks, 36 mo history, higher limits |

Bank sync is **button-only** — no automatic background sync. Push notifications remind users to sync.

## Security

- All internal ports (postgres, redis, vault) closed — only nginx gateway exposed
- CORS restricted to application domains
- HSTS header enabled
- JWT authentication on all endpoints
- Vault for secret storage (banking tokens)
- HMRC fraud prevention headers validated
- GDPR compliant with full Privacy Policy

## Legal Pages

| Page | URL |
|---|---|
| Terms of Service | `/terms` |
| Privacy Policy | `/privacy` |
| Cookie Policy | `/cookies` |
| EULA | `/eula` |

UK law (England and Wales). GDPR compliant. ICO ready.

## Documentation

| File | Content |
|---|---|
| `ROADMAP_TODO.md` | 4-phase launch plan with 109 checkboxes |
| `MONETIZATION_PLAN.md` | Provider comparison, 7 revenue streams, unit economics |
| `BANK_SYNC_ECONOMICS.md` | Button-only sync model, 92%+ margin per tier |
| `AGENTS.md` | Developer environment setup guide |
| `.env.example` | All configuration with setup instructions |

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile | Expo SDK 51, React Native 0.74.5, TypeScript |
| Web | Next.js 13, React 18, TypeScript |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 15, Redis 7, SQLite (auth/billing) |
| Infrastructure | Docker Compose, nginx, Vault, LocalStack |
| Payments | Stripe (with DEV_MODE fallback) |
| HMRC | OAuth2 + MTD ITSA APIs (sandbox tested) |
| AI | OpenAI API (optional), voice gateway (STT/TTS) |

## Project Stats

- **33 Docker containers** running
- **66 files changed** in this release
- **10,882 lines** of new code
- **14 mobile screens** (Revolut-style design)
- **28 web pages**
- **13 HMRC endpoints** (all sandbox tested)
- **12 mortgage endpoints**
- **5 tax calculators**
- **200+ UK merchant categories**
- **10 languages** supported
- **1,440 lines** of legal documentation

## License

Proprietary. All rights reserved. See `EULA` for details.
