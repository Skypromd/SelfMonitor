# Product & compliance policy (single reference)

This document is the **product policy source of truth** for what the platform must and must not do. Operational detail for agents and developers remains in **`AGENTS.md`**.

## Binding rules

| Area | Rule |
|------|------|
| **Bank sync** | **Button-only.** No background or automatic sync. |
| **HMRC MTD** | **Explicit user confirmation** before any submission to HMRC. No auto-submit. Marketing must not describe MTD as “auto-submission”; use “guided MTD workflow” / “prepare then confirm”. |
| **Mortgage tools** | **Informational only**, not regulated financial advice (FCA-aware wording). |
| **AI assistant** | **General guidance only**, not professional tax or legal advice. |

## Implementation pointers

- **HMRC quarterly submit (`integrations-service`):** When `HMRC_REQUIRE_EXPLICIT_CONFIRM=true`, clients must call  
  `POST .../quarterly-update/draft` → `POST .../quarterly-update/confirm` → `POST .../quarterly-update` with the same report body and `confirmation_token`. See service env: `HMRC_REQUIRE_EXPLICIT_CONFIRM`, `POLICY_SPEC_VERSION`, `HMRC_MTD_DRAFT_TTL_HOURS`, `HMRC_MTD_CONFIRM_TTL_MINUTES`.
- **Consent:** Future work — align `consent-service` scopes (banking, HMRC, AI, marketing) and audit before sync/submit (**Phase 1** in `docs/E2E_PRODUCTION_PROGRAM.md`).

## Versioning

- **`POLICY_SPEC_VERSION`** (env on `integrations-service`) is stored on MTD drafts and confirmation rows for audit. Bump when material policy or declaration text changes.

## Related documents

- **`AGENTS.md`** — project overview, gotchas, how to run services.
- **`docs/LAUNCH_READINESS.md`** — launch checklist and scope.
- **`docs/E2E_PRODUCTION_PROGRAM.md`** — full E2E phases.
