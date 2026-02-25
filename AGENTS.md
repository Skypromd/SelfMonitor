# AGENTS.md

## Cursor Cloud specific instructions

### Architecture

This is a FinTech monorepo for self-employed individuals with 23+ Python (FastAPI) microservices, a Next.js 13 web portal, and a React Native/Expo mobile app. Backend services are orchestrated via Docker Compose; the frontend runs separately.

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
npm install --no-package-lock
npm run dev
```
Dev server runs on `http://localhost:3000`. The `.env.local` file points API requests to `http://localhost:8000/api`.

### Linting

- **Web portal:** `cd apps/web-portal && npx next lint`
- **Python services:** CI runs `python -m compileall services/<service>/app` (see `.github/workflows/ci.yaml`).

### Testing

- **Python services:** Each service has `tests/test_main.py`. Run with `cd services/<service> && pip install -r requirements.txt && python3 -m pytest -q tests/test_main.py`. See CI matrix in `.github/workflows/ci.yaml` for the full list.
- **Web portal:** `npm run build` is the CI check (no dedicated test suite).

### Known Issues

- `qna-service` returns 503 because it uses a deprecated Weaviate Python client (v3 API) that is incompatible with newer `weaviate-client` packages. This is non-blocking for other services.
- Localization keys show as raw keys (e.g. `nav.dashboard`) in the UI because the localization service returns translation keys rather than translated strings. This is cosmetic.
- Docker must be started manually in Cloud Agent VMs: `sudo dockerd &>/tmp/dockerd.log &` (systemd is not available).
