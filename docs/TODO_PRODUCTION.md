# Production readiness — TODO

**Прогресс (последнее обновление: 2026-04-10)**  
Закрыто в репозитории: маркетинг без team seats; таблица планов; smoke gateway; матрица `/health`; JWT feature flags + gating в **analytics-service**; **documents-service** health+БД и логи Celery; runbooks (HMRC, OCR, billing lifecycle, security, ADR agent); скрипты `scripts/smoke_gateway_health.*`.

**Остаток только с прод-окружением / внешними системами:** §16.

Единый чеклист до продакшена. После крупных изменений обновляйте `docs/architecture/SERVICES_MATRIX.md`.

**Сводка:** `docs/LAUNCH_READINESS.md` · **E2E программа:** `docs/E2E_PRODUCTION_PROGRAM.md` · **Политика:** `docs/POLICY_SPEC.md` · **Compose prod:** `docs/COMPOSE_PRODUCTION.md` · **Scope v1:** `docs/production-scope.md` · **Non-goals:** `docs/non-goals.md` · **Стандарт сервиса:** `docs/service-standard.md` · **Go-live:** `docs/GO_LIVE_CHECKLIST.md` · **DR:** `docs/disaster-recovery.md` · **Runbooks:** `docs/runbooks/` (restore-db, compose-postgres-backup, rollback, incident-triage, stripe-webhook-failures и др.)

**Принятые решения:**

- Одна подписка = **один пользователь** (`team_members: 1` во всех планах).
- Лимиты и фичи: **`auth-service` → `PLAN_FEATURES`** + JWT; вывод фич при отсутствии в токене — `libs/shared_auth/plan_limits.py` (`_PLAN_FEATURE_DEFAULTS`).

---

## 0. Продукт и документы

- [x] Убрать из маркетинга **team seats** / несколько пользователей на подписку — исправлено в `LandingPage.tsx`; конкурентный анализ не является продуктовым маркетингом.
- [x] В `auth-service`: `team_members: 1` для всех планов в `PLAN_FEATURES`.
- [x] Таблица план ↔ фичи: **`docs/PLAN_FEATURES_TABLE.md`** (синхрон с кодом); прайс на сайте сверять с ней и лендингом.

---

## 1. Gateway и единая точка входа (`:8000`)

- [x] **nginx** invoice upstream и location (как ранее).
- [x] **Correlation id:** `map` по `X-Request-Id` / `$request_id`, **`add_header X-Request-Id`** клиенту, **`request_id`** в JSON access log, общие заголовки в **`nginx/snippets/proxy_common.conf`** / **`proxy_ws.conf`**.
- [x] **Compose:** `docker-compose.prod.yml`, `docker-compose.staging.yml`, шаблоны **`.env.prod.example`** / **`.env.staging.example`** — см. **`docs/COMPOSE_PRODUCTION.md`**.
- [x] Фронт invoices через gateway (как ранее).
- [x] Мобильные клиенты: комментарии к `EXPO_PUBLIC_API_GATEWAY_URL` в `apps/mobile/src/services/api.ts` и `I18nContext.tsx` — прод только через публичный gateway.
- [x] Проверка smoke: **`scripts/smoke_gateway_health.sh`** / **`.ps1`** после `docker compose up`.

---

## 2. Здоровье сервисов и CI

- [x] **gitleaks** в **`.github/workflows/ci.yaml`** (скан секретов в истории коммитов).
- [x] Контракт **`/health`** и исключения: **`docs/HEALTH_ENDPOINTS.md`**.
- [x] Пример job smoke через gateway: **`docs/runbooks/GATEWAY_SMOKE_CI.md`** (включите в workflow при готовности compose на раннере).
- [x] **graphql-gateway** задокументирован (`docs/architecture/GRAPHQL_GATEWAY.md`).
- [x] **ai-agent vs agent:** **`docs/ADR_010_AGENT_SERVICE_CANONICAL.md`**.

---

## 3. Лимиты тарифов (enforcement)

- [x] banking-connector, transactions-service, documents-service (как ранее).
- [x] **analytics-service:** middleware по JWT `plan` / фичам (`mortgage_reports`, `advanced_analytics`, `cash_flow_forecast`); токены без ключа `plan` не режутся (совместимость тестов/legacy).
- [x] **auth-service:** в JWT добавлены `mortgage_reports`, `advanced_analytics`, `cash_flow_forecast`; в **`GET /subscription/plans`** добавлен план **growth**.

---

## 4. Биллинг и trial

- [ ] **billing-service:** Stripe **prod** и реальные webhooks (нужны ключи и тест на стенде).
- [x] Webhook: при наличии **`STRIPE_SECRET_KEY`** (не dev) обязательны **`STRIPE_WEBHOOK_SECRET`** и заголовок **Stripe-Signature**; идемпотентность по **`stripe_webhook_events`**.
- [x] Состояния и синхронизация с auth: **`docs/BILLING_SUBSCRIPTION_LIFECYCLE.md`**.
- [ ] Downgrade / expiry: автотесты end-to-end (частично описано в документе выше).

---

## 5. Документы и OCR (`documents-service`)

- [x] Пайплайн и ретраи: **`docs/OCR_PIPELINE.md`** (Celery, статусы; расширение `autoretry` — roadmap).
- [x] Замена отладочных `print` на **`logging`** в `app/celery_app.py`.
- [x] `/health` учитывает **БД** (`SELECT 1`).
- [ ] Тесты: полный smoke upload → OCR (mock) — расширить при необходимости.

---

## 6. Инвойсы и PDF (`invoice-service`)

- [x] Базовые автотесты (как ранее).
- [ ] PDF в CI с WeasyPrint в Linux — опционально.
- [x] Интеграционная проверка через gateway: см. **`scripts/smoke_gateway_health.*`** (`/api/invoices/health`).

---

## 7. Аналитика и налоги (Starter / Growth)

- [ ] Тесты P&L из **transactions-service** (контрактные — отдельная задача).
- [x] Cash-flow как часть Growth: отражено в `PLAN_FEATURES` и gating **`/forecast/cash-flow`**.
- [x] **tax-engine:** разделение estimate vs submit в **`services/tax-engine/README.md`**.

---

## 8. Календарь и налоговые сроки

- [x] Целевой контур и тесты (roadmap): **`docs/CALENDAR_AND_TAX_DEADLINES.md`**.

---

## 9. HMRC MTD (Pro+)

- [x] Env и двухфазный submit: **`docs/runbooks/HMRC_INTEGRATIONS_ENV.md`**, **`HMRC_REQUIRE_EXPLICIT_CONFIRM`**, draft/confirm в **integrations-service**.
- [x] Идемпотентность токена подтверждения (повторное использование →403); audit полей policy version в SQLite.
- [ ] **tax-engine** + **mtd-agent:** один сквозной сценарий без дублирования — доработка кода.
- [ ] E2E против **HMRC test-api** в CI с секретами.

---

## 10. AI-ассистент (Pro)

- [x] Стратегия зафиксирована: **`docs/ADR_010_AGENT_SERVICE_CANONICAL.md`** (вариант B по смыслу — единый `agent-service`).

---

## 11. Поиск по документам (Pro)

- [ ] Реализация индексации/поиска и лимиты — в backlog; см. также **qna-service**.

---

## 12. Mortgage / BI-стиль отчёты (Pro)

- [x] Решение: основной контур отчётов — **analytics-service**; отдельный **business-intelligence** в compose — опционально позже (матрица сервисов).

---

## 13. REST API доступ (Pro)

- [x] **API keys** в **auth-service** (создание / список / отзыв, обмен на JWT): **`docs/API_KEYS.md`**.
- [x] Rate limit **nginx** для `POST /api/auth/token/api-key` (`nginx/nginx.conf`).
- [x] Audit: событие **`api_key_exchanged`** в **`security_events`** при успешном обмене.
- [ ] Расширенный audit (все попытки, в т.ч. неуспешные) — опционально.
- [x] Roadmap: **`docs/PRO_ROADMAP_API_PARTNERS_COMPLIANCE.md`**.

---

## 14. Business (без команд)

- [ ] partner-registry / referral: продуктовая реализация.
- [ ] White-label: шаблоны и права — по продукту.
- [ ] Централизованный compliance audit — roadmap в том же документе.

---

## 15. Безопасность и операции

- [x] **`docs/THREAT_MODEL.md`**, **`docs/SECURITY_CHECKLIST.md`**, **`docs/OPERATIONS_BACKUP_AND_MONITORING.md`** (шаблоны и чеклисты).
- [x] Продуктовый контур v1 и границы: **`docs/production-scope.md`**, **`docs/non-goals.md`**; операционные шаблоны: **`docs/GO_LIVE_CHECKLIST.md`**, **`docs/disaster-recovery.md`**, **`docs/runbooks/restore-db.md`**, **`docs/runbooks/rollback.md`**, **`docs/runbooks/incident-triage.md`**, **`docs/runbooks/stripe-webhook-failures.md`**.
- [ ] Фактическое включение CORS/rate-limit/бэкапов на прод-инфраструктуре — ops.

---

## 16. Вне репозитория / требуют прод

- Полный прогон **Stripe live** webhooks и подписей.
- **HMRC** E2E job с секретами в CI.
- Включение **API keys**, **partner** rules, **централизованного audit store** в коде.

---

## Быстрый порядок внедрения (рекомендация)

1. П. 0–1 (продукт + gateway smoke).
2. П. 2–3 (health-доки + лимиты + JWT фичи).
3. П. 4–6 (billing prod, документы, инвойсы).
4. П. 7–9 (аналитика, календарь, MTD).
5. П. 10–14 по выручке.
6. П. 15–16 непрерывно и на проде.

---

*Последнее обновление: 2026-04-10.*
