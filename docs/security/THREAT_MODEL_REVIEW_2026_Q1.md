# Threat Model Review (2026 Q1)

Date: 2026-02-17
Owner: Security Engineering + Platform Team
Review scope: Auth, Web Security Center, Mobile Shell, Session and Alerting controls

## 1. Scope and trust boundaries

In scope:
- `services/auth-service` authentication, sessions, MFA, emergency lockdown, risk alerts
- `apps/web-portal` Security Center (`/security`)
- `apps/mobile` native shell security widget, secure storage, auth bridge
- Alert dispatch webhooks for email/push channels

Primary trust boundaries:
- Client (browser/mobile) <-> API boundary
- API <-> external delivery providers (email/push webhooks)
- Token issuance and refresh boundary (access vs refresh token)
- Privileged actions boundary (step-up protected endpoints)

Out of scope:
- Third-party provider internals (email/push vendors)
- Device OS-level compromise
- Company IAM and CI cloud account compromise

## 2. Critical assets

- Access tokens and refresh tokens
- User credentials and password hashes
- MFA secrets (TOTP seed)
- Security event telemetry and session metadata
- Account lifecycle state (`is_active`, `locked_until`, `token_version`)

## 3. Threat analysis (STRIDE-oriented)

### Spoofing
- Stolen refresh token replay
- Session fixation through stale tokens
- Fake login attempts from rotating IPs

Mitigations:
- Refresh token rotation and revocation
- Token version checks and forced invalidation
- Per-IP login rate limits and account lockout

### Tampering
- Unauthorized change to security posture (disable 2FA, revoke controls)
- Event stream manipulation

Mitigations:
- Step-up auth on sensitive actions
- Role checks for admin flows
- Append-only in-memory security event timeline with server-side generation

### Repudiation
- User denies sensitive actions

Mitigations:
- Security event tracking for login, MFA, session revocation, lockdown
- Timestamped event metadata (IP, user-agent, reason details)

### Information disclosure
- Leaking auth secrets via logs or API responses

Mitigations:
- No password or TOTP secret in API responses
- Limited event detail payloads
- Secure mobile token storage (`expo-secure-store`)

### Denial of service
- Password spraying and login flood
- Alert-flood abuse

Mitigations:
- Login IP window throttling
- Account lockout policy
- Alert cooldown and bounded retry strategy

### Elevation of privilege
- Accessing admin actions without hardened posture
- Using stale token to run sensitive operations

Mitigations:
- Optional mandatory admin 2FA gate
- Step-up freshness check (`require_recent_auth`)

## 4. New controls introduced in this cycle

- Emergency lockdown endpoint (`POST /security/lockdown`)
- Automatic risk alert dispatch (email/push webhook channels)
- Realtime risk telemetry surfaced in web Security Center
- Mobile one-tap emergency lock action

## 5. Residual risks and follow-ups

1. Push recipient mapping is provider-managed via webhook integration.
   - Follow-up: add signed provider acknowledgements and delivery receipts.
2. In-memory auth/session storage is suitable for controlled environments only.
   - Follow-up: migrate state to durable store with audit retention policy.
3. Risk scoring is rule-based and deterministic.
   - Follow-up: add anomaly baseline model and adaptive thresholds.

## 6. Review cadence and exit criteria

Cadence:
- Full threat model review each quarter
- Delta review for each major auth/mobile release

Exit criteria for go-live:
- No unresolved Critical findings
- No High findings without approved mitigation and deadline
- Verified emergency lockdown, token revocation, and alert delivery drills
