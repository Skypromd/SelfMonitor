# Execution List: Stabilization to Release Readiness

_Last updated: 2026-02-12_

## Sprint 1 (Weeks 1-2) - Build and CI Stabilization

- [x] Create execution list and start implementation
- [x] Fix broken Next.js/TypeScript pages in `apps/web-portal/pages/*`
- [x] Ensure `npx tsc --noEmit` passes in `apps/web-portal`
- [ ] Resolve auth-service dependency/runtime break in local test setup
- [ ] Replace CI test placeholder with real `pytest` execution
- [ ] Expand CI coverage beyond 3 hardcoded services
- [ ] Add frontend checks (`typecheck`, `lint`, `build`) to CI
- [ ] Move dev secrets from hardcoded compose values to env-based setup

## Sprint 2 (Weeks 3-4) - Auth/Security Hardening

- [ ] Replace `fake_auth_check` in critical services
- [ ] Centralize JWT validation in shared library
- [ ] Propagate real user identity across inter-service requests
- [ ] Migrate critical in-memory stores to persistent storage
- [ ] Standardize error handling/retries for inter-service calls

## Sprint 3 (Weeks 5-6) - Release Readiness

- [ ] Add stable smoke/integration pipeline in CI
- [ ] Enforce quality gates (coverage + required checks)
- [ ] Define observability SLO dashboards and alerts
- [ ] Add release checklist (migration, rollback, dependency security)

## Current focus

1. Web portal build stabilization (active)
2. CI workflow hardening
