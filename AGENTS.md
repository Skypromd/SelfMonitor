# AGENTS.md

## Project Overview

**SelfMonitor** — all-in-one tax & finance platform for UK self-employed individuals.

**Core capabilities:**
- HMRC MTD tax filing (quarterly + final declaration) — sandbox tested, 13 endpoints
- 5 tax calculators (PAYE, rental, CIS, dividend, crypto)
- Invoicing with auto-chase, recurring, payment links, PDF generation
- Mortgage advisor: readiness score, affordability, stamp duty, 8 UK lender matching
- Bank sync (button-only, tiered daily limits per subscription)
- AI assistant with voice input, 10 languages
- Receipt OCR via camera
- 33 Docker containers, 14 mobile screens (Revolut-style), 28 web pages

**Key files for context:**
- `README.md` — full feature list, API endpoints, architecture, **web portal deploy** (API rewrites, practolog, nginx)
- `apps/web-portal/.env.example` — template for `NEXT_PUBLIC_*` and operator subdomain
- `ROADMAP_TODO.md` — 4-phase launch plan (109 checkboxes)
- `MONETIZATION_PLAN.md` — providers, 7 revenue streams, unit economics to £1M MRR
- `BANK_SYNC_ECONOMICS.md` — sync model: button-only, no auto-sync, 92%+ margin

**Business rules (never violate):**
- Bank sync: ONLY on button press by user. No background/automatic sync. Ever.
- HMRC submission: ONLY after explicit user confirmation. Never auto-submit. (Naming: do **not** describe `mtd-agent` as “auto-submission” in user-facing or marketing copy — use “guided MTD workflow” / “prepare then confirm”.)
- Mortgage advice: informational only, not financial advice (FCA compliance)
- AI answers: general guidance, not professional tax/legal advice

## Cursor Cloud specific instructions

### Architecture

33 Python (FastAPI) microservices, Next.js 13 web portal, React Native/Expo mobile app (14 screens). Backend orchestrated via Docker Compose; frontends run separately.

### Running the Backend

See `README.md` "Quick Start" section. Key steps:
1. Copy `.env.example` to `.env` and fill in secrets (dev defaults work for local testing).
2. `docker compose up --build -d` from the repo root starts all backend services.
3. The nginx API gateway is at `http://localhost:8000`.

**Gotcha — Alembic services:** The services `user-profile-service`, `transactions-service`, `compliance-service`, and `documents-service` run Alembic migrations on startup (`alembic upgrade head`). If PostgreSQL is not ready yet, these services will fail. Docker Compose `depends_on` handles ordering, but on slow restarts you may need to `docker compose restart <service>` after Postgres is healthy.

**Gotcha — nginx-gateway DNS:** If you restart individual services but not nginx, nginx may cache stale DNS entries and return 502. Restart nginx-gateway after restarting upstream services: `docker compose restart nginx-gateway`.

### Running the Frontend (Web Portal)

```bash
cd apps/web-portal
npm install
npm run dev
```
Dev server runs on `http://localhost:3000`.

**Deploy / API wiring (read `README.md` → “Deploy: web portal ↔ API gateway”):**

- **`apps/web-portal/.env.local`:** Use **relative** `NEXT_PUBLIC_*` URLs (`/api`, `/api/auth`, …) so the browser only talks to **:3000**; `next.config.js` **rewrites** forward `/api/*` to the nginx gateway (default upstream `http://localhost:8000`). Do not point `NEXT_PUBLIC_*` at `http://localhost:8000` in the browser unless nginx CORS is correctly set for every path you call.
- **Operator subdomain `practolog` (optional):** Isolates operator UI in another origin (`sessionStorage` separate from clients). When `NEXT_PUBLIC_ADMIN_SUBDOMAIN_ENABLED=1`, set `NEXT_PUBLIC_ADMIN_HOST` (e.g. `practolog.localhost` dev, `practolog.example.com` prod), `NEXT_PUBLIC_CLIENT_ORIGIN`, `NEXT_PUBLIC_ADMIN_ORIGIN`. Middleware: `apps/web-portal/middleware.ts`. Defaults and examples: `.env.local` comments.
- **nginx:** After changing gateway config, `docker compose up -d --build nginx-gateway`. CORS for direct :8000 access: `nginx/snippets/cors_api_gateway.conf`.
- **Admin login:** `/admin/login`; admin user from bootstrap env, not public `/register`.

### Running the Mobile App (React Native / Expo)

```bash
cd apps/mobile
npm install
npx expo start
```

The app targets Expo SDK 51 / React Native 0.74.5. It connects to the backend at `http://10.0.2.2:8000/api` (Android emulator → host) by default; update `api.ts` for other environments.

**Linting:** `cd apps/mobile && npx eslint . --ext .ts,.tsx`
**TypeScript check:** `cd apps/mobile && npx tsc --noEmit`
**Bundle test (no device needed):** `cd apps/mobile && npx expo export --platform android`

### Linting

- **Web portal:** `cd apps/web-portal && npx next lint`
- **Mobile app:** `cd apps/mobile && npx eslint . --ext .ts,.tsx`
- **Python services:** CI runs `python -m compileall services/<service>/app` (see `.github/workflows/ci.yaml`).

### Testing

- **Python services:** Each service has `tests/test_main.py`. Run with `cd services/<service> && pip install -r requirements.txt && python3 -m pytest -q tests/test_main.py`. See CI matrix in `.github/workflows/ci.yaml` for the full list.
- **Web portal:** `npm run build` is the CI check (no dedicated test suite).
- **Mobile app:** `cd apps/mobile && npx tsc --noEmit && npx expo export --platform android` verifies the bundle builds. No device/emulator is needed for this check.

### New Services (added 2026-03-06)

| Service | Port | Description |
|---|---|---|
| `services/finops-monitor` | 8021 | Financial ops monitor with MTD/ITSA compliance tracking |
| `services/mtd-agent` | 8022 | HMRC MTD workflow agent (orchestrates prepare/submit; **submit only after explicit user confirmation** — same rule as `integrations-service`) |
| `services/voice-gateway` | 8023 | Voice gateway (STT/TTS, WebSocket streaming) |
| `services/ai-agent-service` | 80 | SelfMate AI agent — memory, tools, multi-language |

Test coverage: **37/37 passing** across all four services.

### Spell Check

The repo uses [cspell](https://cspell.org/) configured in `cspell.json`.

- Run: `npx cspell "**/*.{py,ts,tsx,js,json,md,yml,yaml}" --no-progress`
- Expected result: **0 errors**
- When adding new services or files with tech terms, add unknown words to the `words` array in `cspell.json`. Cyrillic `.md` files and demo scripts are in `ignorePaths` — do not remove them.

### Known Issues

- `qna-service` returns 503 because it uses a deprecated Weaviate Python client (v3 API) that is incompatible with newer `weaviate-client` packages. This is non-blocking for other services.
- Localization keys show as raw keys (e.g. `nav.dashboard`) in the UI because the localization service returns translation keys rather than translated strings. This is cosmetic.
- Docker must be started manually in Cloud Agent VMs: `sudo dockerd &>/tmp/dockerd.log &` (systemd is not available). After starting, run `sudo chmod 666 /var/run/docker.sock` so the non-root user can use Docker.
- **`.env` DATABASE_URLs**: After `cp .env.example .env`, the DATABASE_URL values use `@postgres/` but the compose service name is `postgres-master`. Run `sed -i 's|@postgres/|@postgres-master/|g' .env` and also fix the password to match `POSTGRES_PASSWORD` in `.env`.
- **LocalStack**: Requires `LOCALSTACK_ACKNOWLEDGE_ACCOUNT_REQUIREMENT=1` env var (already set in compose). Without it, LocalStack exits immediately.
- **graphql-gateway**: Builds OK but fails at runtime — Python services are REST, not GraphQL subgraphs. Not critical (nginx REST gateway is the primary entry point).
- **Web portal build**: All ESLint/TS errors fixed. `npm run build` passes clean without `ignoreBuildErrors`.
- Several phantom services (fraud-detection, recommendation-engine, etc.) exist in repo but are NOT in docker-compose or nginx. They are backlog features — do not wire them up.
- **Security**: All internal ports (postgres, redis, vault, weaviate) are closed. Only nginx:8000, billing:8024, invoice:8005 are exposed. CORS restricted to localhost:3000/3001.
- **Legal pages**: `/terms`, `/privacy`, `/cookies`, `/eula` — all present and UK-law compliant.
- `business-intelligence` service has `Optional[BackgroundTasks]` in `generate_business_insights` which is incompatible with FastAPI 0.133+. Tests work around this by monkey-patching `fastapi.routing.APIRoute.__init__` before importing the app.
- Python service tests require `AUTH_SECRET_KEY` env var set **before** importing `app.main` (all services read it at module level via `os.environ["AUTH_SECRET_KEY"]`). Each test file sets it at the top.
- `ai-agent-service` uses `langchain` as an optional dependency — all imports are wrapped in `try/except ImportError`. If langchain is not installed the agent falls back to direct OpenAI calls.
- `mtd-agent`: passing an explicit empty string `""` for `openai_api_key` disables OpenAI (does **not** fall back to the `OPENAI_API_KEY` env var). This is intentional for test isolation.
- In `ai-agent-service` conftest, all async fixture methods must use `AsyncMock` (not `Mock`), and `get_available_tools()` must return a `dict`, not a list.
- **Postgres (first boot):** `postgres-master` mounts `infra/postgres/docker-init/` — on an **empty** data directory it creates `db_invoices`, `db_transactions`, `db_compliance`, `db_consent`, `db_documents`, `db_partner`, `db_referral`, and `mlflow` in addition to `POSTGRES_DB`. If you already have a volume from before this init script, create those databases once manually or recreate the volume.
- **integrations-service:** SQLite file must be on a **writable** path. Compose sets `INTEGRATIONS_DB_PATH=/tmp/integrations.db` by default; the app default matches when env is unset locally.
- **auth-service:** `tests/test_auth_service_main.py` targets a removed in-memory user store and is **ignored** via `services/auth-service/pytest.ini`. Use `tests/test_main.py` for the SQLite-backed API.
