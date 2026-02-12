# Execution List: Stabilization to Release Readiness

_Last updated: 2026-02-12_

## Sprint 1 (Weeks 1-2) - Build and CI Stabilization

- [x] Create execution list and start implementation
- [x] Fix broken Next.js/TypeScript pages in `apps/web-portal/pages/*`
- [x] Ensure `npx tsc --noEmit` passes in `apps/web-portal`
- [x] Resolve auth-service dependency/runtime break in local test setup
- [x] Replace CI test placeholder with real `pytest` execution
- [x] Expand CI coverage beyond 3 hardcoded services
- [x] Add frontend checks (`typecheck`, `lint`, `build`) to CI
- [x] Move dev secrets from hardcoded compose values to env-based setup

## Sprint 2 (Weeks 3-4) - Auth/Security Hardening

- [x] Replace `fake_auth_check` in critical services
- [x] Centralize JWT validation in shared library
- [x] Propagate real user identity across inter-service requests
- [x] Migrate critical in-memory stores to persistent storage
- [x] Standardize error handling/retries for inter-service calls

## Sprint 3 (Weeks 5-6) - Release Readiness

- [x] Add stable smoke/integration pipeline in CI
- [x] Enforce quality gates (coverage + required checks)
- [x] Define observability SLO dashboards and alerts
- [x] Add release checklist (migration, rollback, dependency security)

## Current focus

1. Add optional full docker-compose end-to-end nightly workflow
2. Expand broker-based Pact publishing/verification strategy
