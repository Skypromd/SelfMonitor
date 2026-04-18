# Production scope (v1 MVP) — MyNetTax

Цель: **зафиксировать**, что входит в первый продакшен‑релиз, чтобы не тащить в него все 30+ сервисов сразу.

## Контур v1 (UK fintech MVP)

Обязательные компоненты для **первого** прод‑контура:

| Слой | Компонент | Примечание |
|------|-----------|------------|
| Edge | **nginx-gateway** | `:8000` в dev; TLS на edge (LB/Cloudflare). **Рекомендуемый старт v1:** `scripts/compose_v1_up.sh` / **`scripts/compose_v1_up.ps1`** (только сервисы MVP, без «зоопарка»). Prod merge: см. **`docs/COMPOSE_PRODUCTION.md`**. |
| Auth | **auth-service** | JWT, планы, API keys (Pro+), 2FA |
| Profile | **user-profile-service** | |
| Money movement | **transactions-service** | Импорт, лимиты по плану |
| Banking | **banking-connector** | Open Banking, лимиты коннектов |
| Documents | **documents-service** + **Celery** (worker docs) + **S3/MinIO** | Upload, OCR, квота storage |
| Tax / MTD | **tax-engine** + **integrations-service** | Оценки; submit через integrations с **explicit confirm** |
| MTD UX | **mtd-agent** | Оркестрация; не auto-submit |
| Invoicing | **invoice-service** | |
| Billing | **billing-service** | Stripe webhooks, идемпотентность |
| i18n | **localization-service** | Критичные строки |
| Support path (минимум) | **qna-service** + **Weaviate** *или* статичный FAQ на фронте | **Prod по умолчанию (скрипт v1 + `USE_COMPOSE_PROD`):** без вектора (`V1_INCLUDE_QNA_VECTOR=0`) — только FAQ/статика; `/api/qna` не поднимается. **Dev:** векторный QnA включён. |
| Infra (минимум) | **PostgreSQL**, **Redis**, объектное хранилище | Как в compose; в проде — managed |

Клиенты: **web-portal**, **mobile** — только через **публичный gateway** URL.

## В релизе v1, но вторичны (можно включать поэтапно после smoke)

Сервисы в **docker-compose** и за nginx, не блокируют запуск ядра, но увеличивают поверхность:

- **calendar-service**, **consent-service**, **compliance-service**, **categorization-service**
- **advice-service**, **partner-registry**, **referral-service**, **cost-optimization**, **finops-monitor**
- **agent-service** (без обязательного LLM в v1, если ключей нет)
- **support-ai-service** (опционально; без ключа — degraded)

## Не в v1 релизе (позже / отдельный профиль)

| Компонент | Причина |
|-----------|---------|
| **graphql-gateway** | Профиль `graphql`; не блокер для REST MVP |
| **voice-gateway** | Ключи, комплаенс, нагрузка |
| **business-intelligence**, **predictive-analytics** | Не в основном compose |
| **Elasticsearch / Kibana / Weaviate** | Тяжёлая инфра; включать осознанно |
| **MLflow**, лишние **Redis Sentinel** реплики | Упростить v1 при необходимости |

Полный список «всех» сервисов: **`docs/architecture/SERVICES_MATRIX.md`**.

## SLO v1 (стартовые цели — уточнить под нагрузку)

| Метрика | Цель v1 (черновик) |
|---------|---------------------|
| Доступность API (gateway) | 99.5% (без жёсткого SLA на старте) |
| p95 latency gateway → типовый GET | &lt; 500 ms при номинальной нагрузке |
| Error rate (5xx) | &lt; 0.5% за скользящее окно |
| RPO | 24 h (ежедневный бэкап БД) |
| RTO | 4–8 h (ручной restore из runbook) |

Обновляйте таблицу после первых недель prod.

## Связанные документы

- **`docs/non-goals.md`** — что явно не обещаем в v1  
- **`docs/TODO_PRODUCTION.md`** — техдолг и чеклист  
- **`docs/POLICY_SPEC.md`**, **`docs/GO_LIVE_CHECKLIST.md`**
