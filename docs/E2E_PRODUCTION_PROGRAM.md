# Программа вывода в production (E2E) — оценка плана и TODO воплощения

Ниже — оценка **полного 12‑фазного плана** (как у внешнего советника), сопоставление с **текущим репозиторием SelfMonitor** и **практический backlog** для воплощения. Детальный техдолг по сервисам по‑прежнему ведётся в **`docs/TODO_PRODUCTION.md`**.

## Оценка плана

| Критерий | Вердикт |
|----------|---------|
| **Структура** | Сильная: сначала policy/compliance, потом платформа, потом домены (HMRC, банк, биллинг, OCR, AI). |
| **Согласование с вашими правилами** | Совпадает с **`AGENTS.md`**: bank button‑only, HMRC только после explicit confirm, mortgage/AI — disclaimers. |
| **Реалистичность** | Высокая для UK fintech; объём — **много кварталов** команды, не один спринт. |
| **Риск** | Если пытаться сделать все фазы параллельно — срыв сроков; порядок «включения модулей» в плане — правильный. |

**Итог:** план годится как **дорожная карта**; «10/10» по рынку/регулятору достигается итерациями, не одним релизом.

---

## Сводка: фаза плана ↔ что уже есть в репо

| Фаза | Тема | В репозитории сейчас | Главный разрыв |
|------|------|----------------------|----------------|
| **1** | Policy + two‑phase submit + consent | `AGENTS.md`, `docs/LAUNCH_READINESS.md`, `consent-service` в compose | Нет единого **`POLICY_SPEC.md`**; нет **формальной** модели draft→confirm→submit с токеном на бэкенде для MTD |
| **2** | Platform (K8s, env, секреты, миграции, observability) | `infra/k8s`, Vault в compose, Jaeger/Prom/Grafana/Loki в compose | Миграции **на старте** сервисов (gotcha в `AGENTS.md`); нет обязательного **отдельного job** миграций в проде |
| **3** | Security (threat model, RBAC, CI gates) | nginx WAF‑паттерны, JWT, README про безопасность | Нет **`THREAT_MODEL.md` / SECURITY_CHECKLIST.md`**; mTLS/сервисные токены между сервисами — не как стандарт |
| **4** | HMRC prod | `integrations-service` (HMRC env, ретраи, fraud headers), runbooks частично | **Идемпотентность submit**, полный **audit** ответов HMRC, E2E sandbox→prod контур |
| **5** | Banking + transactions | `banking-connector`, лимиты коннектов, `transactions-service` лимит/мес | **Журнал «кто нажал sync»** (audit), **daily limits** как отдельный слой от месячного tx limit |
| **6** | Billing + Stripe | `billing-service`, `auth-service` планы | Stripe **prod** webhooks, **entitlements** как отдельный сервис vs только JWT |
| **7** | OCR | `documents-service` (Celery, S3, OCR), **квота storage по JWT** | PII/redaction для AI, **suggestion vs booked** транзакция из OCR — продуктово довести |
| **8** | AI + voice | `agent-service`, `voice-gateway`, support-ai; GraphQL без субграфов | Многоагентная оркестрация, **tool API** с RBAC, отсутствие утечки PII в LLM |
| **9** | Mortgage info‑only | `analytics-service` mortgage endpoints | Локализованные **дисклеймеры**, логи согласия на раздел |
| **10** | i18n (5 языков) | `localization-service` | Системная связка **locale ↔ план ↔ legal версии**; переводы критических путей |
| **11** | Support / тикеты | `qna-service`, support-ai | Внешняя система (Zendesk/Jira) или единый **ticket store** + SLA — не свёрстано end‑to‑end |
| **12** | QA / rollout | Тесты по сервисам, CI | E2E матрица (5 языков × критические пути), canary/kill‑switch как процесс |

---

## TODO: воплощение по фазам (добавьте в спринты)

### Фаза 1 — Product & Compliance Baseline

- [x] **`docs/POLICY_SPEC.md`**: один источник правды (bank button‑only, HMRC confirm, mortgage info‑only, AI non‑advice) + ссылки на `AGENTS.md`.
- [x] **Two‑phase MTD (integrations-service)**: **draft** → **confirm** → **submit** с `confirmation_token`, fingerprint отчёта и `POLICY_SPEC_VERSION`; при `HMRC_REQUIRE_EXPLICIT_CONFIRM=true` submit без токена — **403**. Идемпотентный submit и тот же контракт в **tax-engine / mtd-agent** — по-прежнему в backlog.
- [ ] **Consent**: расширить использование **`consent-service`**: scopes (banking, HMRC, AI, marketing), журнал версий политики; проверки перед sync/submit.

### Фаза 2 — Platform

- [ ] **Миграции**: вынести `alembic upgrade head` из startup в **init job** / helm hook; задокументировать в runbook.
- [ ] **Окружения**: явные **dev / staging / prod** (отдельные кластеры или проекты), раздельные БД и секреты.
- [ ] **Observability**: correlation-id через nginx → сервисы; SLO/алерты (5xx, p95) — минимум на gateway, HMRC, OCR.

### Фаза 3 — Security

- [ ] **`docs/THREAT_MODEL.md`** (краткий) + **`docs/SECURITY_CHECKLIST.md`** (релизный чеклист).
- [ ] **CI**: dependency scan, container scan, secret scanning (GitHub Actions или аналог).
- [ ] **Сервис‑к‑сервису**: mTLS или подписанные internal JWT (roadmap, не обязательно day 1).

### Фаза 4 — HMRC Production

- [ ] Секреты prod/sandbox, runbook обновлён (`docs/release/HMRC_MTD_DIRECT_RUNBOOK.md` и др.).
- [ ] Идемпотентные ключи submit, статусы, хранение HMRC receipt ids, не двоить отправку.
- [ ] E2E: sandbox обязательно; prod — по процедуре HMRC.

### Фаза 5 — Banking & Transactions

- [ ] **Audit log** ручного sync: user, time, tier, count imported (отдельная таблица или событие).
- [ ] **Daily sync limits** по тарифу (если в продукте заявлено) — слой поверх/рядом с месячным лимитом транзакций.

### Фаза 6 — Billing & Invoicing

- [ ] Stripe prod: webhooks, подпись, маппинг планов ↔ `PLAN_FEATURES`.
- [ ] Решение: **entitlements только JWT** vs отдельный **entitlements API** — зафиксировать и реализовать единообразно.

### Фаза 7 — OCR

- [ ] Негативные сценарии: низкий confidence → обязательный review; автосоздание транзакции только как **draft/suggestion** до подтверждения пользователем (согласовать с `transactions-service`).

### Фаза 8 — AI & Voice

- [ ] Архитектура агентов (orchestrator vs один `agent-service`) — ADR.
- [ ] Логи: model version, template version; запрет «совета» в mortgage на уровне prompt/policy.

### Фаза 9 — Mortgage

- [ ] UI/юридические **дисклеймеры** на всех 5 языках для mortgage‑экранов; логирование просмотра.

### Фаза 10 — i18n (EN, PL, RO, UA, RU)

- [ ] `user.locale` + fallback EN; критические строки и legal — версии и переводы.
- [ ] Синхронизация с **планом** (какие языки доступны по подписке) — уже частично в `auth-service`; довести до UI+API.

### Фаза 11 — Support

- [ ] Выбор: встроенные тикеты vs интеграция Zendesk/Jira; единый **P0/P1** маршрут и шаблоны на 5 языков.

### Фаза 12 — QA & Rollout

- [ ] Матрица тестов: unit (policy, entitlements), integration (HMRC, Stripe, OCR), E2E критический путь.
- [ ] Canary, rollback, feature flags для «тяжёлых» модулей.

---

## Рекомендуемый порядок включения модулей (как в исходном плане)

Совпадает с **`docs/LAUNCH_READINESS.md`** и здравым смыслом:

1. Core + MTD (draft/confirm/submit) + audit + базовая поддержка  
2. Banking + categorization + лимиты  
3. Billing + подписки  
4. Invoicing  
5. OCR/documents  
6. AI (текст)  
7. Voice  
8. Mortgage (info-only)  
9. Расширение KB и агентов  

---

## Связь с существующими документами

| Документ | Назначение |
|----------|------------|
| `docs/TODO_PRODUCTION.md` | Пошаговый техдолг по сервисам (nginx, тесты, лимиты, MTD, …). |
| `docs/LAUNCH_READINESS.md` | Go/no-go и must-have перед публичным продом. |
| `docs/runbooks/FULL_STACK_DOCKER.md` | Запуск полного compose. |
| `AGENTS.md` | Неснимаемые бизнес‑правила. |

**Этот файл (`E2E_PRODUCTION_PROGRAM.md`)** — мост между «стратегическим» 12‑фазным планом и **конкретными задачами в репо**; обновляйте чекбоксы по мере выполнения.

---

*Создано для сопоставления внешнего E2E плана с кодовой базой SelfMonitor.*
