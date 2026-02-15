# Observability SLO Dashboards and Alerts

This document defines the baseline SLOs and dashboard sections used for release readiness.

## 1. SLOs

### API availability SLO
- **Target:** 99.5% monthly availability for public API paths.
- **Source metric:** `up{job="fintech-app"}` and request success ratio.
- **Error budget:** ~3h 39m per 30-day month.

### API error-rate SLO
- **Target:** 5xx rate below 1% over rolling 30 days.
- **Fast-burn alert threshold:** 5% over 10 minutes.
- **Source metric:** `http_requests_total`.

### Latency SLO
- **Target:** p95 latency < 800ms for core user flows.
- **Fast-burn alert threshold:** p95 > 800ms for 10 minutes.
- **Source metric:** `http_request_duration_seconds_bucket`.

## 2. Grafana dashboard structure

Create one dashboard per environment (`dev`, `staging`, `prod`) with these panels:

1. **Availability**
   - Uptime by service (`up`).
   - Availability percentage by service/job.
2. **Reliability**
   - 4xx/5xx request rate split.
   - 5xx percentage over time.
3. **Latency**
   - p50/p95/p99 request latency.
   - Endpoint-level latency top-N.
4. **Traffic**
   - Requests per second by service and endpoint.
   - Request volume heatmap by hour.
5. **System pressure**
   - CPU and memory per service.
   - Restart count / container health trend.

## 3. Alerting policy

Prometheus rule file:
- `observability/alerts/slo_alerts.yml`

Alert severities:
- `critical`: service down (`FintechServiceDown`)
- `warning`: SLO burn-risk (`FintechApiHighErrorRate`, `FintechApiHighP95Latency`)

Routing recommendations:
- `critical` -> paging channel (on-call)
- `warning` -> engineering Slack + incident triage board

## 3.1 HMRC MTD reliability SLO overlay

For direct HMRC submission operations, monitor these additional service-level targets:

- Success rate target:
  - `HMRC_SLO_SUCCESS_RATE_TARGET_PERCENT` (default 99%)
- Latency target:
  - `HMRC_SLO_P95_LATENCY_TARGET_MS` (default 2500ms)

Operational endpoints:
- `GET /integrations/hmrc/mtd/submission-slo`
- `GET /integrations/hmrc/mtd/operational-readiness`

Recommended HMRC dashboard panels:
1. Rolling success rate (%)
2. p95 submission latency (ms)
3. Direct vs simulated transmission split
4. Fallback count trend
5. Credential rotation overdue indicator

## 4. Operational checklist for alerts

When an SLO alert fires:
1. Confirm blast radius (`service`, `endpoint`, `time window`).
2. Correlate with deploy/event timeline.
3. Check dependencies (DB, Redis, external integrations).
4. Mitigate (rollback, traffic shaping, feature-flag).
5. Record postmortem items and update SLO dashboard annotations.

