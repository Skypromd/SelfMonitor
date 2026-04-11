# Матрица сервисов `services/*`

Снимок по репозиторию: **docker-compose.yml**, **nginx/nginx.conf** (`:8000`), тесты. Ниже — **назначение** и **ожидаемая работоспособность** (без запуска контейнеров в CI; фактически проверяйте `docker compose ps` и `/health`).

## Как читать колонку «Работа»

| Метка | Смысл |
|-------|--------|
| **OK (через :8000)** | В основном `docker-compose` и есть маршрут в **nginx** → с фронта вызывается как `http://localhost:8000/api/...`, если gateway и сервис healthy. |
| **OK (другой порт)** | Поднимается compose'ом, но **не** за nginx на 8000; доступ напрямую по указанному порту. |
| **OK (GraphQL)** | Поднимается compose'ом; HTTP API на **`:4000`**, в nginx на `:8000 не проксируется**. |
| **Не в стеке** | Нет в корневом `docker-compose.yml` → **сам не стартует** при обычном `docker compose up`. |
| **Частично** | В стеке, но без маршрута в nginx **или** без автотестов **или** нужны внешние ключи (HMRC, Stripe, LLM). |

---

## Таблица: назначение и работоспособность

| Сервис | Работа (ожидание) | Назначение |
|--------|-------------------|------------|
| **advice-service** | OK (через :8000) | Финансовые советы и рекомендации на основе данных пользователя. |
| **agent-service** | OK (через :8000) | Прикладной агент: сценарии вокруг транзакций, документов, налогового расчёта (не путать с отдельным **ai-agent-service**). |
| **ai-agent-service** | Не в стеке | См. **`docs/ADR_010_AGENT_SERVICE_CANONICAL.md`**: канонический контур — **agent-service**; GraphQL env не должен ссылаться на «пустые» имена субграфов. |
| **analytics-service** | OK (через :8000) | Аналитика, отчёты, ипотечные и продуктовые эндпоинты; часть маршрутов ограничена по JWT **`plan`** и фичам из `PLAN_FEATURES` (middleware в `app/main.py`). |
| **auth-service** | OK (через :8000) | Регистрация, JWT, 2FA, профиль сессии, планы подписки (MVP). |
| **banking-connector** | OK (через :8000) | Open Banking: провайдеры, счета, импорт транзакций (часто с mock в dev). |
| **billing-service** | Частично | Счета, Stripe, внутренний учёт; **OK через :8000**, но реальные платежи требуют **Stripe env**. |
| **business-intelligence** | Не в стеке | BI-отчёты и агрегации; образ есть, **в compose не подключён**. |
| **calendar-service** | OK (через :8000) | События, сроки, напоминания (в т.ч. в связке с налогами). |
| **categorization-service** | OK (через :8000) | Категории и правила разметки транзакций (UK-мерчанты и т.д.). |
| **compliance-service** | OK (через :8000) | Комплаенс, AML/KYC-сигналы, регуляторная логика. |
| **consent-service** | OK (через :8000) | Учёт согласий (GDPR и др.). |
| **cost-optimization** | OK (через :8000) | Рекомендации и метрики по оптимизации расходов. |
| **customer-success** | Не в стеке | Вовлечённость пользователей; **не в compose**. |
| **documents-service** | OK (через :8000) | Документы, OCR, пайплайны разбора и ревью. |
| **finops-monitor** | OK (через :8000) | FinOps-мониторинг (сигналы по деньгам/операциям). |
| **fraud-detection** | Не в стеке | Антифрод; **не в compose**. |
| **graphql-gateway** | OK (GraphQL) | Apollo Federation на **:4000**; в корневом compose включён **только с `--profile graphql`** (см. `docs/architecture/GRAPHQL_GATEWAY.md`). REST-сервисы без `/graphql` не являются субграфами до отдельной реализации. |
| **integrations-service** | Частично | Фасад HMRC и др.; **OK через :8000**, реальная отправка в HMRC — **ключи и sandbox/prod**. |
| **international-expansion** | Не в стеке | Заготовка под международные сценарии; **без тестов в репо**. |
| **invoice-service** | OK (через :8000) | Инвойсы, PDF; в compose также **:8005** для прямого dev-доступа; **маршрут `/api/invoices/`** в `nginx/nginx.conf`. |
| **ipo-readiness** | Не в стеке | Оценка «IPO readiness»; **не в compose**. |
| **localization-service** | OK (через :8000) | Каталоги переводов для UI (i18n). |
| **mtd-agent** | Частично | Оркестрация MTD-потоков (не «автосабмит»): согласовано с `AGENTS.md` — submit только после явного подтверждения пользователя; **OK через :8000**. |
| **partner-registry** | OK (через :8000) | Партнёры, реферальные и B2B-сущности. |
| **predictive-analytics** | Не в стеке | Прогнозная аналитика; **не в compose**. |
| **pricing-engine** | Не в стеке | Динамическое ценообразование; **не в compose**. |
| **qna-service** | OK (через :8000) | База знаний Q&A для поддержки. |
| **recommendation-engine** | Не в стеке | Рекомендации; **нет в compose и без тестов в дереве**. |
| **referral-service** | OK (через :8000) | Реферальные коды и награды. |
| **security-operations** | Не в стеке | SecOps; **не в compose**. |
| **security-service** | Частично | Доп. security API; **в compose есть**, **в nginx на :8000 нет** — снаружи основного API **не торчит**. |
| **strategic-partnerships** | Не в стеке | B2B/альянсы; **не в compose**. |
| **support-ai-service** | Частично | AI для саппорта; **OK через :8000**, **автотестов в репо не найдено**. |
| **tax-engine** | Частично | Расчёт налогов и сценарий submit; **OK через :8000**, HMRC — через integrations. |
| **tenant-router** | Не в стеке | Маршрутизация тенантов; **не в compose**, минимальный тест импорта. |
| **transactions-service** | OK (через :8000) | Транзакции, счета, черновики чеков, сверка. |
| **user-profile-service** | OK (через :8000) | Профиль, настройки, данные пользователя (PostgreSQL). |
| **voice-gateway** | Частично | STT/TTS/WebSocket; **OK через :8000**, нужны **ключи/модели** для прод-качества. |

---

## Исходная техническая матрица (compose / nginx / тесты)

| Сервис | `docker-compose` | Маршрут в **nginx** (`:8000`) | Тесты (pytest и т.п.) |
|--------|------------------|-------------------------------|-------------------------|
| advice-service | да | да (`/api/advice/`) | да |
| agent-service | да | да (`/api/agent/`) | да |
| ai-agent-service | нет | нет | да |
| analytics-service | да | да (`/api/analytics/`) | да |
| auth-service | да | да (`/api/auth/`) | да |
| banking-connector | да | да (`/api/banking/`) | да |
| billing-service | да | да (`/api/billing/`) | да |
| business-intelligence | нет | нет | да |
| calendar-service | да | да (`/api/calendar/`) | да |
| categorization-service | да | да (`/api/categorization/`) | да |
| compliance-service | да | да (`/api/compliance/`) | да |
| consent-service | да | да (`/api/consent/`) | да |
| cost-optimization | да | да (`/api/cost-optimization/`) | да |
| customer-success | нет | нет | да |
| documents-service | да | да (`/api/documents/`) | да |
| finops-monitor | да | да (`/api/finops/`) | да |
| fraud-detection | нет | нет | да |
| graphql-gateway | да (profile **`graphql`**) | нет — **`:4000`** | нет |
| integrations-service | да | да (`/api/integrations/`) | да |
| international-expansion | нет | нет | нет |
| invoice-service | да | да (`/api/invoices/`) | да (pytest smoke) |
| ipo-readiness | нет | нет | нет |
| localization-service | да | да (`/api/localization/`) | да |
| mtd-agent | да | да (`/api/mtd/`) | да |
| partner-registry | да | да (`/api/partners/`) | да |
| predictive-analytics | нет | нет | да |
| pricing-engine | нет | нет | да |
| qna-service | да | да (`/api/qna/`) | да |
| recommendation-engine | нет | нет | нет |
| referral-service | да | да (`/api/referrals/`) | да |
| security-operations | нет | нет | нет |
| security-service | да | нет | нет |
| strategic-partnerships | нет | нет | нет |
| support-ai-service | да | да (`/api/support/`) | нет |
| tax-engine | да | да (`/api/tax/`) | да |
| tenant-router | нет | нет | да (`test_import.py`) |
| transactions-service | да | да (`/api/transactions/`) | да |
| user-profile-service | да | да (`/api/profile/`) | да |
| voice-gateway | да | да (`/api/voice/`) | да |

## Пояснения

- **Nginx** — HTTP из `nginx/nginx.conf` под `/api/...`. **GraphQL** — отдельно на **4000**.
- **Не в compose** — не стартует с обычным `docker compose up`.
- **Тесты** — факт наличия файлов, не гарантия покрытия.

Обновляйте документ при изменении `docker-compose.yml` или `nginx/nginx.conf`.
