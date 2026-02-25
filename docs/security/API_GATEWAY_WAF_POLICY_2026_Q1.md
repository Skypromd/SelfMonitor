# API Gateway WAF / Anti-Automation Policy (2026 Q1)

## Scope

Applies to `nginx-gateway` entrypoint in `docker-compose.yml` and all `/api/*` routes.

## Active controls

1. **Rate limiting**
   - Global per-IP limit: `30 r/s` with controlled burst.
   - Stricter auth endpoints:
     - `/api/auth/token`
     - `/api/auth/register`
2. **Connection limits**
   - Per-IP concurrent connection cap to reduce bot fan-out and abuse spikes.
3. **Signature-based block rules**
   - Scanner user-agents (e.g., sqlmap/nikto/nmap-like probes) are blocked.
   - Suspicious URI patterns are blocked (path traversal, script injection payloads, hidden repo/env probes).
4. **Method hardening**
   - Requests with unsupported HTTP methods are rejected (`405`).
5. **Gateway hardening headers**
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy: strict-origin-when-cross-origin`
6. **WAF observability**
   - Structured JSON gateway logs include WAF reason fields.
   - Promtail extracts WAF labels for Loki/Grafana triage.

## Operational guidance

- Start with current thresholds and tune based on production telemetry.
- Keep allow-list exceptions minimal and time-bound.
- Treat repeated `403`/`429` spikes as potential abuse indicators and review source IP/user-agent clusters.
- Couple gateway data with auth security events for correlated incident response.
- Use `docs/observability/WAF_MONITORING_AND_ALERTS.md` for dashboard queries and alert handling.

## Change management

- Any threshold relaxation must include a security rationale in release notes.
- Quarterly policy review is required as part of threat-model refresh.
