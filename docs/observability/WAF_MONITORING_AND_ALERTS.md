# WAF Monitoring and Alerting Guide

This guide defines how to observe anti-automation and WAF controls on `nginx-gateway`.

## 1. Log telemetry baseline

Gateway access logs are emitted in structured JSON (`waf_json`) with fields:

- `status`
- `request_uri`
- `request_time`
- `waf_bad_ua`
- `waf_bad_uri`
- `waf_block_reason`

Promtail parses and labels these fields for container `nginx-gateway`.

## 2. Grafana/Loki panel queries

Use Loki with range selectors such as:

1. **Blocked requests by reason (5m):**
   ```logql
   sum by (waf_block_reason) (
     count_over_time({job="containerlogs",container="nginx-gateway",waf_block_reason!="none"}[5m])
   )
   ```

2. **429 trend (rate-limit pressure):**
   ```logql
   sum(count_over_time({job="containerlogs",container="nginx-gateway",status="429"}[5m]))
   ```

3. **403 trend (WAF signature blocks):**
   ```logql
   sum(count_over_time({job="containerlogs",container="nginx-gateway",status="403"}[5m]))
   ```

4. **Top targeted paths during block spikes:**
   ```logql
   topk(20, sum by (request_uri) (
     count_over_time({job="containerlogs",container="nginx-gateway",status=~"403|429"}[15m])
   ))
   ```

## 3. Prometheus alerts (service-level proxy)

Prometheus rule file `observability/alerts/slo_alerts.yml` includes:

- `FintechApiHigh429Rate`
- `FintechApiHigh403Volume`

These are service-level proxy alerts based on application metrics. During incidents, correlate with nginx Loki logs to confirm whether traffic is malicious or legitimate.

## 4. Triage flow

When `403/429` alerts fire:

1. Confirm whether spikes are isolated to one route/client pattern.
2. Verify `waf_block_reason` distribution (bad UA vs bad URI signatures).
3. Check for false positives against known customer paths.
4. If malicious:
   - maintain/strengthen current limits and signatures,
   - notify security on-call.
5. If false positives:
   - tune signature/rate limits,
   - record change with timestamp and reason.

## 5. Release gate checks

Before rollout:

- ensure nginx structured WAF logs are enabled;
- ensure promtail label extraction works for `status` and `waf_*` fields;
- verify alert routes for `FintechApiHigh429Rate` and `FintechApiHigh403Volume`.
