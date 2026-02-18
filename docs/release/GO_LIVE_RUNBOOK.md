# Go-Live Runbook

This runbook is used for production go-live and patch releases.

## 1. Scope and owners

- Release commander: owns execution timeline.
- On-call engineer: owns alerts and rollback decision.
- Backend owner: validates API and migrations.
- Frontend owner: validates admin/web portal critical paths.

## 2. Preconditions

- CI is green (`python-services`, `web-portal`, `smoke-core-flow`).
- No unresolved critical incidents in current environment.
- Release notes are finalized and approved.
- A rollback target (previous stable image/tag) is available for every changed service.

## 3. Preflight checks (T-30 minutes)

From repository root:

```bash
python3 tools/release_preflight.py --quick
```

Recommended full preflight before major releases:

```bash
python3 tools/release_preflight.py --include-frontend
```

## 4. Deployment sequence

1. Freeze feature merges to `main` during rollout window.
2. Capture backup/restore point for production databases.
3. Apply migrations for changed services (partner-registry included).
4. Deploy backend services in controlled waves.
5. Deploy web portal after backend API health is confirmed.
6. Monitor logs and SLO dashboards for at least 15 minutes before widening traffic.

## 5. Post-deploy monetization verification

Use admin console and/or API checks to verify:

1. Lead lifecycle updates still work (`initiated -> qualified -> converted/rejected`).
2. Billing report loads for selected date range and statuses.
3. Invoice generation returns expected fields:
   - `invoice_number` format: `INV-YYYYMM-######`
   - `due_date` present and valid
4. Invoice artifacts are downloadable:
   - PDF export (`/billing/invoices/{id}/pdf`)
   - Accounting CSV (`target=xero`, `target=quickbooks`)

## 6. Success criteria

- No elevated 5xx rate compared to pre-release baseline.
- p95 latency remains within SLO thresholds.
- No auth or RBAC regression for protected monetization endpoints.
- Finance operations can generate at least one invoice and download both CSV mappings.

## 6.1 Auth security gate (mandatory)

Before enabling production traffic, validate these auth controls:

1. Password and account protection:
   - `AUTH_PASSWORD_MIN_LENGTH` is at least `12`.
   - `AUTH_MAX_FAILED_LOGIN_ATTEMPTS` and `AUTH_ACCOUNT_LOCKOUT_MINUTES` are configured.
2. Session/token protection:
   - refresh rotation works (`POST /auth/token/refresh`).
   - revoke endpoints are reachable:
     - `POST /auth/token/revoke`
     - `GET /auth/security/sessions`
     - `DELETE /auth/security/sessions/{session_id}`
     - `POST /auth/security/sessions/revoke-all`
   - emergency lockdown endpoint is reachable:
     - `POST /auth/security/lockdown`
3. Verification/MFA protection:
   - email verification flow works:
     - `POST /auth/verify-email/request`
     - `POST /auth/verify-email/confirm`
   - admin posture is hardened (`AUTH_REQUIRE_ADMIN_2FA=true` in production).
4. Step-up protection:
   - sensitive actions reject stale access tokens (step-up required).
5. Audit visibility:
   - `GET /auth/security/events` returns recent auth events for test user.
6. Risk alert delivery:
   - `AUTH_SECURITY_ALERTS_ENABLED=true` in production.
   - at least one test alert is delivered over both configured channels (`email`/`push`).
   - provider setup validated:
     - email: `webhook` or `sendgrid`
     - push: `webhook`, `expo`, or `fcm`
   - webhook channels use request signing (`AUTH_SECURITY_ALERT_WEBHOOK_SIGNING_SECRET`).
   - receipt ingestion is enabled for provider callbacks:
     - `AUTH_SECURITY_ALERT_RECEIPTS_ENABLED=true`
     - `POST /auth/security/alerts/delivery-receipts` accepts signed receipts.
   - cooldown (`AUTH_SECURITY_ALERT_COOLDOWN_MINUTES`) is set to prevent alert floods.

## 6.2 Threat-model and pentest gate (mandatory)

Before scaling traffic beyond pilot:

1. Threat model is up to date for current release:
   - `docs/security/THREAT_MODEL_REVIEW_2026_Q1.md`
2. External pentest package is completed:
   - `docs/security/EXTERNAL_PENTEST_PLAYBOOK_2026_Q1.md`
   - latest pentest report is attached to release evidence.
3. No unresolved Critical findings and no High findings without approved risk acceptance.

## 6.3 IP protection and anti-cloning gate (mandatory)

Before broad release and partner onboarding:

1. Legal visibility:
   - Proprietary repository license exists at `/LICENSE`.
   - Web/mobile legal routes are reachable:
     - `/terms`
     - `/eula`
2. Export attribution controls:
   - export watermarking is enabled (`PARTNER_EXPORT_WATERMARK_ENABLED=true`);
   - export headers are present (`X-SelfMonitor-Export-Watermark`) on CSV/PDF downloads.
3. Gateway anti-automation posture:
   - nginx-gateway WAF/rate-limit policy is active:
     - global API rate limit;
     - stricter auth burst control (`/api/auth/token`, `/api/auth/register`);
     - suspicious scanner/path signatures are blocked with `403`.
4. Mobile attestation gate:
   - mobile attestation is enabled (`AUTH_MOBILE_ATTESTATION_ENABLED=true`);
   - sensitive mobile endpoints require attestation headers:
     - `/auth/mobile/security/push-tokens`
     - `/auth/mobile/security/lockdown`

## 7. Exit and handover

- Announce release completion with validation summary.
- Keep heightened monitoring for at least one hour.
- Record issues and follow-up actions in release notes.

## 8. Agent safe mode operations

Use safe mode whenever downstream write actions show instability or abnormal error spikes:

1. Keep chat/read-only guidance enabled.
2. Disable write execution only by setting:
   - `AGENT_WRITE_ACTIONS_ENABLED=false`
3. Redeploy `agent-service`.
4. Verify expected behavior:
   - `POST /agent/chat` still responds.
   - `POST /agent/actions/execute` returns `write_actions_disabled`.
5. Track incident timeline in release notes and audit review.

## 9. Rollback and feature flag procedure

When a partial rollback is preferred over full version rollback:

1. Apply feature-flag rollback first:
   - disable agent writes (`AGENT_WRITE_ACTIONS_ENABLED=false`);
   - keep read-only advisory traffic online.
2. If issue persists, perform service rollback using `docs/release/ROLLBACK_DRILL.md`.
3. After rollback/safe mode:
   - run `python3 tools/release_preflight.py --quick`;
   - verify dashboard KPIs:
     - agent action success rate,
     - human override rate,
     - OCR review completion time,
     - tax submission conversion rate.

## 10. HMRC direct submission hardening checks

Before enabling or continuing direct HMRC mode in production:

1. Validate operational readiness:
   - `GET /integrations/hmrc/mtd/operational-readiness`
2. Validate reliability trend:
   - `GET /integrations/hmrc/mtd/submission-slo`
3. Confirm OAuth credential rotation metadata is current:
   - `HMRC_OAUTH_CREDENTIALS_ROTATED_AT`
   - `HMRC_OAUTH_ROTATION_MAX_AGE_DAYS`
4. Ensure fallback policy is explicitly set:
   - `HMRC_DIRECT_FALLBACK_TO_SIMULATION=true|false`

Detailed procedure:
- `docs/release/HMRC_MTD_DIRECT_RUNBOOK.md`

## 11. Compliance-critical incident handling

If HMRC submission reliability or filing integrity is at risk:

1. Enter incident mode and assign compliance owner.
2. Evaluate direct-to-simulation fallback.
3. Capture SLO/readiness snapshots before and after mitigation.
4. Complete postmortem using:
   - `docs/release/COMPLIANCE_INCIDENT_POSTMORTEM_TEMPLATE.md`
