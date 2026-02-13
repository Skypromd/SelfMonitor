# Execution List: Stabilization to Release Readiness

_Last updated: 2026-02-13_

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
3. [x] Enforce RBAC on monetization lead reports (`billing:read` scope / admin role)
4. [x] Make lead deduplication race-safe in PostgreSQL (advisory lock + transactional insert)
5. [x] Introduce Alembic baseline for `partner-registry` and migration-ready schema checks
6. [x] Add lead lifecycle statuses (`initiated/qualified/rejected/converted`) and billable-first reports
7. [x] Surface monetization billing tools in web admin panel (status updates + billing export)
8. [x] Add pricing ops, lead feed, and invoice lifecycle in monetization admin workflows
9. [x] Add invoice numbering policy, PDF export, and Xero/QuickBooks CSV mappings
10. [x] Add go-live runbook, rollback drill, and monetization smoke gate expansion
11. [x] Close security pass: upgrade web dependencies and lock reproducible npm install
12. [x] Restore receipt scanning output for expense article and deductible hints
