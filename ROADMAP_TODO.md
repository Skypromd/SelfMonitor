# MyNetTax — Roadmap & Checklist

## Текущий статус проекта

- **33 Docker-контейнера** работают
- **HMRC MTD compliance**: fraud headers, quarterly updates, final declaration, loss adjustments, BSAS
- **Web portal** билдится без хаков, регистрация → логин → дашборд работает
- **2 новых сервиса**: referral-service (13/13 тестов), cost-optimization (14/14 тестов)
- **Billing**: DEV_MODE с mock checkout работает

---

## Фаза 0: Запуск (до первого пользователя)

### Получение API-ключей (ваша задача)

- [ ] **Stripe**: зарегистрироваться на https://dashboard.stripe.com/test/apikeys
  - [ ] Скопировать `STRIPE_SECRET_KEY` (sk_test_...)
  - [ ] Скопировать `STRIPE_WEBHOOK_SECRET` (whsec_...)
  - [ ] Создать 4 продукта в Stripe: Starter £12, Growth £15, Pro £18, Business £28 (ex VAT)
  - [ ] Скопировать Price ID для каждого
  - [ ] Прописать всё в `.env`

- [ ] **HMRC**: зарегистрироваться на https://developer.service.hmrc.gov.uk
  - [ ] Создать Sandbox Application
  - [ ] Подписаться на MTD ITSA API
  - [ ] Скопировать `HMRC_OAUTH_CLIENT_ID` и `HMRC_OAUTH_CLIENT_SECRET`
  - [ ] Прописать в `.env`
  - [ ] Протестировать quarterly submission в sandbox
  - [ ] Протестировать final declaration в sandbox
  - [ ] Подать заявку на Production Credentials

- [ ] **Домен и хостинг**
  - [ ] Купить домен (selfmonitor.app / selfmonitor.co.uk)
  - [ ] Арендовать VPS (DigitalOcean 8GB RAM / AWS t3.large)
  - [ ] Настроить DNS (A-запись → IP сервера)
  - [ ] Настроить SSL (Cloudflare бесплатно или Let's Encrypt)

### Безопасность (до продакшна обязательно)

- [ ] Сгенерировать `POSTGRES_PASSWORD`: `openssl rand -hex 32`
- [ ] Сгенерировать `AUTH_SECRET_KEY`: `openssl rand -hex 64`
- [ ] Сгенерировать `VAULT_DEV_ROOT_TOKEN_ID`: `openssl rand -hex 32`
- [x] CORS: `billing-service` и прочие — список origin из env (`ALLOWED_ORIGINS` / аналоги), не `*` в проде
- [ ] Закрыть порты 5432, 6379, 8080 в firewall (оставить только 80, 443)
- [ ] Убрать `AUTH_BOOTSTRAP_ADMIN=true` после создания первого admin аккаунта

---

## Фаза 1: "Работает лучше всех" (4-6 недель)

### 1.0 CIS Refund & obligations (MVP value, UK)
- [x] Модель обязательств: агрегация по UK tax month × contractor (ключ `contractor_key`) → статусы **MISSING / VERIFIED / UNVERIFIED / NOT_CIS** в API `GET /cis/refund-tracker` (+ существующие `cis_review_tasks` / `cis_records`)
- [x] Напоминания: `next_reminder_at` при скане; throttle **72h hard + 2/7d soft** — `GET /cis/reminders/notification-eligible`, `POST /cis/reminders/{id}/mark-sent`; snooze **7 / 14 / 30** дней
- [x] UI «CIS Refund Tracker»: страница `/cis-refund-tracker`, навигация + дашборд
- [x] Сверка statement ↔ bank: поля `reconciliation_status`, `bank_net_observed_gbp` на `cis_records`; **needs_review** при расхождении с `net_paid_total`

### 1.1 Open Banking — автоимпорт транзакций из банков
- [x] **Провайдер:** Salt Edge — основной (`BANKING_OPEN_BANKING_PROVIDER=saltedge`, `POST /connections/initiate`, Connect session → callback с `connection_id`)
- [x] OAuth / consent: Salt Edge Connect (выбор банка на стороне Salt Edge); TrueLayer — запасной путь в коде для демо без ключей Salt Edge
- [x] Импорт транзакций при callback + окно до **90 дней** где применимо (`banking-connector`)
- [x] **Prod:** только sync по кнопке (`AGENTS.md`); фоновый авто-sync не включать
- [x] UI: `/connect-bank` — провайдеры с `logo_url`, бейдж Recommended для Salt Edge, сетка UK-банков с иконками; мобилка — чипы провайдеров из API
- [ ] Регистрация и ключи Salt Edge в вашем `.env` / прод; fake bank → staging → production
- [ ] Опционально: TrueLayer sandbox только для нагрузочного теста API (не обязательно для продукта)

### 1.2 Smart Auto-categorization
- [x] Глобальная таблица merchant → категория: JSON (`CATEGORIZATION_MERCHANT_RULES_PATH`), порядок: per-user learn → глобальные правила → статический UK-словарь → LLM; `GET /merchant-rules`, `POST /internal/merchant-rules` + `CATEGORIZATION_INTERNAL_TOKEN`
- [x] 200+ строк merchant-паттернов UK + расширяемый список; Amazon/eBay → `cost_of_goods`, банки → `bank_charges`, доставка еды и т.д.
- [x] Fallback: `categorization-service` (`/categorize`, LLM при наличии ключа)
- [x] UI: смена категории → `POST /categorization/learn` (web + mobile; mobile также после flush офлайн-очереди)
- [x] Подготовить данные для ML модели (фаза 2) — `scripts/export_categorization_training_sample.py` → CSV из `CATEGORIZATION_MERCHANT_RULES_PATH` (или локальный JSON)

### 1.3 Receipt OCR
- [x] Заменить LocalStack Textract mock на реальный AWS Textract — конфиг в `.env.example` (без endpoint URL + ключи/роль; `DOCUMENTS_OCR_TEXTRACT_API=expense`)
- [x] Парсить: дата, сумма, merchant name, VAT amount (web review + Textract detect/expense; prod — `DOCUMENTS_OCR_TEXTRACT_API=expense`)
- [x] Автосоздание транзакции из распознанного чека — Celery после OCR + создание черновика при подтверждении/исправлении ревью, если не было `receipt_draft_transaction_id`; VAT в описании черновика
- [x] UI: кнопка "Scan receipt" → камера → результат — `documents.tsx` (`capture="environment"`, загрузка как раньше)
- [x] Мобильное приложение: нативная камера через Expo — `ReceiptScanScreen` (`expo-image-picker`, задняя камера, VAT в сохранении)

### 1.4 Push-уведомления о дедлайнах
- [x] Email-уведомления: за 14, 7, 3, 1 день до MTD дедлайна — `finops-monitor` APScheduler 08:05 UTC, SMTP + `GET /internal/reminder-recipients` в auth-service
- [x] Push (Expo Push Notifications) для мобильного приложения — регистрация `POST /finops/mtd/me/expo-push-token` (Redis), те же окна что и email; `syncMtdPush` после логина; production: EAS `projectId` в `app.json` / `extra.eas.projectId`
- [x] In-app карточка MTD на дашборде (web + mobile) + дедлайны кварталов в Deadlines / Tax summary
- [x] Auto-reminder если квартальная подача не сделана за 24 часа до дедлайна — письмо «urgent-pending» при `days_left <= 1` и статусе квартала ≠ `submitted` (дедуп Redis)

### 1.5 Экспорт CSV/Excel
- [x] Transactions → CSV с фильтрами (даты, категории) — web `transactions.tsx`
- [x] Invoices → CSV списка (пагинация) — web; PDF по каждому инвойсу — по-прежнему отдельно
- [x] Tax report → **PDF summary для бухгалтера** — `tax-preparation.tsx` и `submission.tsx` (jsPDF + таблицы категорий / MTD)
- [x] **Bookkeeping CSV** — колонки Income_gbp / Expense_gbp для Excel (не файл отправки в HMRC)
- [x] Отдельный CSV «MTD-style digital records» на `tax-preparation.tsx` (дата, income/expense, категория, VAT из текста описания, id) — не файл API-отправки в HMRC

### 1.6 Мобильное приложение в App Store / Google Play
- [x] Экран **Subscription**: данные **billing-service** (`/billing/subscription/{email}`, `/billing/addons`) + покупка **CIS accountant consult** через `POST /billing/checkout/session` → Stripe Checkout (тот же шлюз `EXPO_PUBLIC_API_GATEWAY_URL`, что и остальные API); **`useFocusEffect`** — обновление Stripe-блока при каждом возврате на экран (после браузера/Checkout).
- [ ] Apple Developer Account ($99/год)
- [ ] Google Play Developer Account ($25 единоразово)
- [ ] `eas build --platform ios` + `eas build --platform android`
- [ ] App Store Connect: скриншоты, описание, privacy policy
- [ ] Google Play Console: listing, content rating
- [ ] Submit на review

---

## Фаза 1.5: Mortgage Advisor — killer-фича (параллельно с Фазой 1)

Ни один конкурент (FreeAgent, QuickBooks, Xero) не помогает с ипотекой.
Для self-employed получить ипотеку в UK — главная боль (отказ в 3 раза чаще чем employed).
У нас уже есть: 9 endpoints, 1675 строк, 14 типов ипотеки, readiness assessment, PDF pack.

### 1.5.1 AI Mortgage Advisor (мультиязычный)
- [x] Режим `POST /chat` с `context.advisor_mode: "mortgage"` — отдельный системный блок (UK multiples, self-employed оговорки, FCA-style «не совет по ипотеке»)
- [x] Контекст: профиль + financial_context из memory (доход/налоги и т.д.); tax returns / инвойсы в контекст — расширять отдельно
- [x] Мультиязычность: параметр `language` (в т.ч. pl, ro, uk)
- [x] UK mortgage rules в промпте; fallback: whole-of-market broker + in-app mortgage tools
- [x] UI: `/assistant` — чекбокс «Mortgage readiness» и `?mode=mortgage` → прямой `POST /chat` с `context.advisor_mode`

### 1.5.2 Affordability Calculator
- [x] Max mortgage (планирование): employed **4.5×**, self-employed **3–4×** (база **3.5×**) — `analytics-service` `POST /mortgage/affordability`
- [x] Сценарии по банкам (illustrative): Barclays / HSBC / Halifax / Nationwide / NatWest — те же caps от дохода в ответе API
- [x] Ежемесячный платёж (annuity repayment) и срок **5–40** лет; номинальная ставка задаётся пользователем
- [x] Stress: **+3 п.п.** к номинальной ставке → отдельный месячный платёж
- [x] SDLT England: first-time buyer до £625k (рельеф), standard marginal bands, +3% surcharge для additional property (упрощённо)
- [x] Web **Reports**: блок «Mortgage affordability» + кнопка **Fill income from tax estimate** (`/calculate` 2025/26)

### 1.5.3 Lender Comparison (реальные банки)
- [x] Иллюстративные строки в `POST /mortgage/affordability` (multiples / min history / notes):
  - [x] Barclays-style: 1 год, 4.49×, 10% deposit
  - [x] HSBC-style: 2 года, 4×, 10%
  - [x] Halifax-style: 2 года, retained profit note
  - [x] Nationwide-style: 2 года, 4.5×
  - [x] NatWest-style: 2 года, 4×, contractors note
  - [x] Specialist (illustrative): Kensington, Pepper Money, Together — в `POST /mortgage/affordability`
- [x] Иллюстративный **matching**: `credit_band` (clean / minor / adverse), `years_trading`, авто **deposit %** → `illustrative_fit_score` + причины, сортировка сценариев (не % одобрения)
- [x] Фильтры: property type (residential / leasehold flat / BTL), CCJ past 6y self-report — `POST /mortgage/affordability` + Reports UI; `planner_notes` + `credit_band_effective`
- [x] Обновление данных кредиторов каждый квартал — в ответе `POST /mortgage/affordability`: `illustrative_lenders_as_of` + `illustrative_lenders_pack_version` (bump в `mortgage_affordability.py` при пересмотре сценариев)

### 1.5.4 Document Auto-fill
- [x] SA302 (часть) — в broker ZIP: `hmrc-mortgage-document-status.json` (совпадения имён файлов с SA302/TY overview) + `hmrc-income-tax-estimate.json` через `POST …/integrations/hmrc/mtd/tax-calculation` (симуляция/песочница; **не** официальный PDF HMRC)
- [x] Tax Year Overview (часть) — JSON расчёта через HMRC **Individual Calculations** API: `GET/POST …/integrations/hmrc/self-assessment/{tax_year}/calculations…` (integrations-service; при `HMRC_DIRECT_SUBMISSION_ENABLED` — реальный HMRC); broker ZIP опционально с NINO → `hmrc-individual-calculation.json`
- [x] Tax Year Overview — официальный **PDF** из PTA: в broker ZIP `hmrc-official-tax-evidence-steps.txt` (gov.uk PTA + SA302 guidance) + загрузка PDF в Documents (чеклист); не автозагрузка (нет HMRC API)
- [ ] Tax Year Overview — автоматическая выгрузка PDF из PTA без входа пользователя на gov.uk (только если появится поддерживаемый HMRC/OAuth документ-flow)
- [x] Income & Expenditure form — иллюстративный preview из linked bank: `GET /mortgage/money-preview` (analytics → transactions-service); UI Reports → «Linked bank money preview» + JSON/CSV (не statutory)
- [x] Bank statements — CSV из banking-connector: `GET /exports/statement-csv` (rolling window, default 180d); данные из `transactions/me` после ручного sync; UI на `/connect-bank`
- [x] Business accounts summary — UK tax-year P&L rollups в том же `GET /mortgage/money-preview` (до 6 лет; illustrative, не certified accounts)
- [x] Один клик → стартовый пакет для broker-а: `POST /mortgage/broker-bundle.zip` (pack index JSON + money preview JSON + optional CSV из banking-connector); UI Reports — «Download broker starter bundle (ZIP)»

### 1.5.5 Broker Marketplace
- [ ] Партнёрство с 10-20 mortgage brokers специализирующихся на self-employed
- [ ] Broker получает: готовый mortgage pack + readiness score + income verification
- [ ] Юзер выбирает broker-а → бронирует консультацию (бесплатно для юзера)
- [ ] Revenue: £200-500 за квалифицированный лид (стандарт индустрии)
- [ ] Отзывы и рейтинги broker-ов от юзеров
- [ ] Фильтр: языки broker-а (EN, PL, RO, UA — для нашей аудитории мигрантов)

### 1.5.6 Mortgage Progress Tracker ("Дорога к ипотеке")
- [x] Timeline: 7 шагов (credit → deposit → accounts → tax → debts → pack → apply) — `POST /mortgage/progress-tracker`
- [x] Авто-сигналы: месяцы банковской истории + число документов (если `include_backend_signals` и сервисы доступны)
- [x] Текущий шаг: первый незавершённый; депозит с **progress_ratio**; ETA депозита при monthly savings
- [x] Web **Reports**: блок «Road to mortgage», кнопка **Use last readiness %**
- [x] Push / email при смене шага Road to mortgage (finops weekly + `POST /internal/mortgage-milestones/run`; первый замер без рассылки; дедуп перехода; при ошибке SMTP/push — сброс дедупа и повтор на следующем запуске; без каналов — только обновление шага в Redis)
- [x] Ежемесячный сводный email/push прогресса ипотеки (finops 10-го числа 09:35 UTC + `POST /internal/mortgage-monthly-digest/run`; дедуп `mortgage:monthly_digest:*`)

---

## Фаза 2: "Делает то, чего другие не умеют" (6-10 недель)

### 2.1 AI Tax Advisor на родном языке
- [x] Режим `context.advisor_mode: "tax"` — системный блок UK IT/NI/PA/MTD (информация, не замена бухгалтеру)
- [x] Контекст: профиль + financial_context из memory; мультиязычность — параметр `language` (как у остального чата)
- [ ] Отдельный fine-tune модели — не делали (достаточно промпта + RAG позже)
- [x] UI: `/assistant` — Focus «UK tax», ссылка с `tax-preparation` на `/assistant?mode=tax`

### 2.2 Voice input
- [x] Интент-парсер: распознать "заплатил 50 фунтов за бензин" → {amount: 50, category: Fuel, currency: GBP} — `parse_expense_intent`, `POST /voice/quick-intent`, `POST /voice/transcribe-intent`
- [x] Поддержка 4 языков: EN, PL, RO, UK — ключевые слова в `expense_intent.py` + тесты
- [x] Интеграция с voice-gateway (STT уже есть)
- [x] Мобильное приложение: кнопка микрофона на главном экране — `screens/DashboardScreen.tsx` (4s запись → transcribe-intent)

### 2.3 MTD prep reminders (no auto-submit)
- [x] За **3 дня** до дедлайна: письмо/push дополняется текстом «подготовьте черновик / review → confirm → submit»; флаг `mtd_draft_prep_hint` в событии Redis
- [x] Автосбор черновика quarterly в БД без входа пользователя — finops tier‑3 → tax-engine `/internal/mtd/auto-draft-quarterly` → integrations `/internal/hmrc/mtd/quarterly-update/draft` (JWT mint + business retention для расчёта; dedup Redis)
- [x] **Нет** фоновой подачи в HMRC (как и раньше)
- [x] Напоминания tier 14/7/3/1 не шлются, если квартал уже `submitted` (исправлена логика tier-1)

### 2.4 Real-time profit dashboard
- [x] WebSocket endpoint: новая транзакция → push на дашборд (`/api/finops/ws/dashboard/live`, finops + transactions notify)
- [x] Виджеты: "Profit today", "Profit this week", "Tax owed so far" (`GET /insights/profit-pulse`, tax-engine YTD при `include_tax_estimate`)
- [x] Графики: недельный net profit (8 недель, Recharts) на дашборде
- [x] Сравнение с прошлым годом: delta по той же календарной неделе (~364 дня назад)

### 2.5 Tax savings tips
- [x] База подсказок: trading allowance, flat-rate home office (~£312/г), mileage, phone split — `GET /insights/tax-savings`
- [x] Персонализация по категориям транзакций за выбранный tax year (`start_date` / `end_date`)
- [x] Web: блок «Tax-saving ideas» на `tax-preparation.tsx`
- [x] Push раз в месяц — `finops-monitor` cron 15-го числа 09:10 UTC, Expo dedup `tax_tips:monthly_push:*`, текст → Tax preparation

### 2.6 Instant invoice payments
- [x] Stripe Payment Links: `POST /invoices/{id}/payment-link` (Stripe Payment Link API), UI «Pay link» / иконка на `invoices.tsx`
- [x] Клиент получает email при создании ссылки (если `client_email` + SMTP); ссылка «Pay now» в письме
- [x] Webhook: `POST /webhooks/stripe/invoices` — `checkout.session.completed` → запись оплаты (Stripe) + статус paid через `update_invoice_status_from_payments`
- [x] Уведомление продавцу: email + Expo push через `POST /internal/notify-invoice-paid` (finops-monitor), dedup по `checkout_session_id`

---

## Фаза 3: "Viral growth" (10-16 недель)

### 3.1 Реферальная программа 2.0
- [x] £25 credit за каждого приглашённого друга (обоим) — `POST /internal/account-credit` (billing), idempotency `referral-{usage_id}-referrer|referee`; signup `?ref=` → `POST /internal/apply-signup-referral`; `validate-referral` тоже начисляет
- [x] Месяц Pro бесплатно для топ-10 рефереров — billing cron 1-го числа 07:00 UTC: `GET /internal/top-referrers` (прошлый месяц) → `referral_leaderboard_pro_until` конец текущего месяца; `GET /subscription/{email}` отдаёт effective `pro` для free/starter/growth
- [x] Leaderboard: `GET /leaderboard` + позиция пользователя; web `referrals.tsx` (поля `referral_count` / `total_earned`)
- [x] Sharing: ссылка `{origin}/register?ref=CODE&plan=starter`, QR (api.qrserver.com), `GET /me/referral-code`
- [x] Email-кампания: finops cron 5-го числа 10:15 UTC, dedup `marketing:referral_invite:*`, SMTP как MTD reminders

### 3.2 Бесплатный MTD калькулятор (SEO-магнит)
- [x] Лендинг: `/tax-calculator-uk` + `POST /public/self-employed-estimate` (tax-engine, без JWT)
- [x] Без регистрации: доход/расходы → Income Tax + NI + SL + take-home (модель `calculate_self_employed_tax`, 2025/26-style)
- [x] CTA на странице → `/register`
- [x] SEO на 10 языках: отдельные локализованные лендинги — `/tax-calculator-uk` (EN) + `/tax-calculator-uk/{pl,ro,uk,ru,es,it,pt,tr,bn}`; `hreflang`/`canonical` при `NEXT_PUBLIC_SITE_ORIGIN`; детальный чеклист ниже

#### 3.2 Языковой TODO (лендинги калькулятора)

**Политика перевода (смысл + UK-практика)**

- Переводим **смысл и контекст**: вводные абзацы, пояснения к полям, дисклеймеры, CTA, «как читать результат» — так, чтобы носитель языка понял риски и ограничения без потери точности.
- **Не переводим** (оставляем **латиницей / как в UK**): официальные имена и аббревиатуры **HMRC**, **MTD**, **Self Assessment**, **ITSA** (если используете в копи), **NI** (National Insurance), **Student Loan**, валюта и суммы **£ / GBP**, ссылки **gov.uk**, названия продуктов в интерфейсе, если они совпадают с тем, что пользователь увидит в письмах от HMRC/в англоязычном кабинете.
- **Глоссарий при первом упоминании** (мировая практика для регулируемых тем): короткий родной эквивалент + **оригинал в скобках**, напр. польск. вводка + «*Income Tax (подоходный налог в системе UK)*» — дальше по тексту можно **Income Tax**, чтобы не плодить неофициальные «канцеляризмы», которых нет в законе.
- **SEO**: заголовок и description локализуются под запросы диаспоры; в теле допустимы **гибридные** формулировки (*self employed*, *UK tax*), потому что так реально ищут; не подменять официальные термины вымышленными ключами.
- **Редактор**: носитель языка + сверка с EN-оригиналом по чеклисту терминов; юридический дисклеймер — не «литературный», а **юридически эквивалентный по смыслу** (не обещать консультацию).

**Общая инфраструктура (один раз)**

- [x] Стратегия URL: префикс `/tax-calculator-uk/[lang]` (код: `pages/tax-calculator-uk/[lang].tsx`)
- [x] Общий React-компонент калькулятора + вынесенные строки/копирайт по локали (`components/TaxCalculatorPublic.tsx`, `lib/taxCalculatorSeoCopy.ts`)
- [x] `<title>` / meta description / OG на каждую локаль
- [x] `hreflang` + `canonical` между EN и локалями (при заданном `NEXT_PUBLIC_SITE_ORIGIN` в `.env.example`)
- [x] Публикация в `sitemap.xml` (+ при необходимости `robots.txt`) — `/sitemap-seo-tax-calculator.xml` (rewrite → SSR XML), `/robots.txt` → `Sitemap: …/sitemap-seo-tax-calculator.xml`; `locale: false` в `next.config.js` rewrites
- [ ] Юридический блок: «информация, не совет» — проверенный перевод / локальный редактор (черновик копи в коде; финальный legal review)

**По языкам** (каждый: уникальный вводный текст + SEO-ключи + ревью дисклеймера; калькулятор тот же API)

- [x] **EN** — `/tax-calculator-uk` (база)
- [x] **PL**
- [x] **RO**
- [x] **UA**
- [x] **RU**
- [x] **ES**
- [x] **IT**
- [x] **PT**
- [x] **TR**
- [x] **BN**

### 3.3 Партнёрство с accountants
- [ ] Accountant portal: бухгалтер видит всех клиентов, их данные, подачи
- [ ] Bulk MTD filing: подать за 50 клиентов одним нажатием
- [ ] Revenue share: бухгалтер получает £3/мес за каждого клиента
- [ ] Outreach: email 500 UK accounting firms

### 3.4 Контент на 10 языках
- [ ] Блог: "How to pay taxes in UK as self-employed" — EN, PL, RO, UA, RU, ES, IT, PT, TR, BN
- [ ] YouTube: 5-минутные гайды на каждом языке
- [ ] SEO оптимизация каждой статьи
- [ ] Цель: 50K органического трафика/мес за 3 месяца

### 3.5 Community
- [ ] Telegram группы: "Self-employed UK 🇬🇧" по языкам
- [ ] Модерация + еженедельные Q&A
- [ ] Бот в группе: "/tax 50000" → расчёт налога
- [ ] Cross-promotion в Facebook группах диаспор

### 3.6 Freemium модель
- [x] Free: **20** транзакций/мес — `PLAN_FEATURES["free"]` в **auth-service** + fallback `_DEFAULT_FREE` в **`libs/shared_auth/plan_limits`** (JWT `transactions_per_month_limit`); **1 банк** / **no MTD direct** уже в тех же лимитах.
- [x] Starter (лимиты в коде): **3** банка, **999999** tx/мес (практический unlimited), MTD guided (`hmrc_submission`), 1×/day sync — `PLAN_FEATURES["starter"]` + fallback-мапы **`_BANK_CONNECTIONS_BY_PLAN`** / **`_TRANSACTIONS_PER_MONTH_BY_PLAN`** в `plan_limits`. Публичные £ — **billing** `PLANS` / лендинг (£12 ex VAT).
- [x] Growth / Pro: лимиты и флаги — `PLAN_FEATURES`; публичный прайс и копирайт — лендинг + **pricing-engine** `GET /pricing-plans`.
- [x] Business: **multi-business (MVP)** — **transactions-service**: `user_businesses` + `transactions.business_id`, опциональный заголовок **`X-Business-Id`**, `GET/POST/PATCH /businesses` (второй+ бизнес только при `plan=business`, макс. **10**); импорт/списки транзакций и receipt-draft учитывают бизнес. **CIS / refund-tracker** пока по-прежнему на весь `user_id` без разреза по бизнесу.

---

## Фаза 4: "Платформа" (16-24 недели)

### 4.1 Marketplace
- [ ] Страховка для self-employed (партнёрство с Simply Business / Hiscox)
- [ ] Пенсия (партнёрство с Nest / PensionBee)
- [ ] Бизнес-кредиты (партнёрство с Funding Circle / iwoca)
- [ ] Revenue model: £5-50 за каждый лид

### 4.2 Business bank account
- [ ] Партнёрство с Tide или Starling
- [ ] Embedded banking: открыть счёт прямо из MyNetTax
- [ ] Автоматический sync без Open Banking OAuth
- [ ] Revenue: £2-5/мес revenue share

### 4.3 IR35 checker
- [ ] Вопросник на основе HMRC CEST tool
- [ ] AI анализ контракта (upload PDF → определение статуса)
- [ ] Рекомендации по структурированию контракта
- [ ] Уникальная фича — ни один конкурент не делает

### 4.4 Multi-business
- [x] Один аккаунт = несколько бизнесов — **MVP в transactions-service** (см. §3.6 Business).
- [x] Раздельный учёт **транзакций** (и receipt-flow) по `business_id`; Primary-бизнес по умолчанию (детерминированный UUID).
- [ ] Объединённый tax report по всем бизнесам + раздельный MTD по юрлицам — **не** в MVP.
- [ ] FreeAgent НЕ умеет — конкурентное преимущество (маркетинг; после полного tax-split)

### 4.5 Accountant portal
- [ ] Расширить support-portal для бухгалтеров
- [ ] Client management: список клиентов, статусы подач
- [ ] Bulk actions: подать MTD за всех клиентов
- [ ] Messaging: чат бухгалтер ↔ клиент внутри приложения

### 4.6 Public API
- [ ] REST API с OAuth2 для third-party разработчиков
- [ ] Документация (Swagger/OpenAPI)
- [ ] Webhooks: transaction.created, invoice.paid, mtd.submitted
- [ ] Developer portal с sandbox

---

## KPI по фазам

| Фаза | Срок | Ключевая метрика | Цель |
|---|---|---|---|
| 0 | Неделя 1-2 | Продукт доступен онлайн | ✅ Live |
| 1 | Неделя 3-8 | Day-30 Retention | >60% |
| 2 | Неделя 9-16 | NPS | >50 |
| 3 | Неделя 17-24 | Viral coefficient | >1.2 |
| 4 | Неделя 25-36 | MRR | £40K+ |

---

## Бюджет

| Статья | Стоимость/мес |
|---|---|
| VPS (8GB RAM) | £40-80 |
| Домен | £10/год |
| Apple Developer | £80/год |
| Google Play | £20 единоразово |
| AWS Textract (OCR) | £1 за 1000 страниц |
| TrueLayer (Open Banking) | Бесплатно до 500 юзеров |
| Stripe | 1.4% + 20p за транзакцию |
| HMRC API | Бесплатно |
| OpenAI API (AI advisor) | ~£50-200/мес при 1000 юзеров |
| **Итого** | **~£150-400/мес** |

Break-even: ~30-45 платящих юзеров на Starter (£9/мес)

---

## CIS variant B (self-attested) — compliance, UI, security, accountant

**Принцип:** verified CIS (есть statement) vs **UNVERIFIED** self-attested; гейты на submit/export; жёсткий audit trail; консультация бухгалтера как страховочный слой.

### Сделано в коде (фундамент)

- [x] **libs/shared_mtd** — `MTDQuarterlyCISDisclosure` в quarterly report (fingerprint/hash).
- [x] **libs/shared_cis** — `CISEvidenceStatus`, `CISRecordBase`, `CISAttestationRecord`, enum **`CISAuditAction`** (имена событий для compliance-service).
- [x] **tax-engine** — поля `cis_tax_credit_verified_gbp`, `cis_tax_credit_self_attested_gbp`, `unverified_cis_submit_acknowledged`; legacy `cis_suffered_in_period_gbp` → весь объём считается **unverified**; при split-полях legacy игнорируется с флагом в breakdown; `breakdown.cis_credits_breakdown`; гейт на `/calculate-and-submit` при unverified без ack; MTD payload включает `cis_disclosure` + `unverified_cis_submit_acknowledged`.
- [x] **integrations-service** — гейт на quarterly submit если `credit_self_attested_unverified_gbp > 0` без ack; лог `cis_unverified_submit_confirmed`; в тело к HMRC **`cis_disclosure` не уходит** (только внутренний отчёт/хэш).
- [x] **web-portal** — `Badge` variant `unverified`, `CisComplianceBanner`, страница **tax-preparation**: секция CIS, копирайт про UNVERIFIED и accountant review.

### P0 Security & audit (продолжить)

- [x] Fail-fast **AUTH_SECRET_KEY** — `libs/shared_auth/auth_secret_preflight.py` + `jwt_fastapi` / `plan_limits`; при `DEPLOYMENT_PROFILE|APP_ENV` = production/prod или `AUTH_SECRET_KEY_PREFLIGHT_STRICT=1` — длина ≥32, иначе задать `AUTH_ALLOW_WEAK_JWT_SECRET=1` (как auth-service); **support-ai-service** — только `os.environ`, без пустого дефолта
- [x] Единый preflight в **auth-service** — `app/config.py` вызывает `resolve_auth_secret_key()` + прежнее правило ≥32 символа без `AUTH_ALLOW_WEAK_JWT_SECRET`; Docker **context: .** + `libs/` в образе; тесты добавляют корень репо в `sys.path`
- [x] Per-user **hash-chain** для `audit_events` в **compliance-service** (`prev_chain_hash`, `chain_hash`, SHA-256 над предыдущим хэшем + каноническим JSON; genesis = 64×`0`); старые строки без цепочки остаются `NULL` / следующее событие цепляется от genesis. Append-only по API (без update/delete событий).
- [x] **`CISAuditAction`** → `POST .../audit-events` из **transactions-service** (`crud_cis`, shared `post_audit_event`) при ключевых шагах.
- [x] Событие **`cis_unverified_submit_confirmed`** в compliance при ack на quarterly submit — **integrations-service** (если задан `COMPLIANCE_SERVICE_URL`).
- [x] **`mtd_quarterly_submitted`**, **`mtd_final_declaration_submitted`** — **integrations-service** после успешного quarterly / при приёме final-declaration (`COMPLIANCE_SERVICE_URL`).
- [x] Писать audit из **documents-service** — `POST /documents/upload` → `document_uploaded`; `PATCH /documents/{id}/review` → `document_review_updated` (если `COMPLIANCE_SERVICE_URL` / `DOCUMENTS_COMPLIANCE_SERVICE_URL` задан)
- [x] Писать audit из **tax-engine** — `POST /calculate` (`tax_calculate`), `POST /mtd/prepare` (`tax_mtd_prepare`), `POST /calculate-and-submit` (`tax_calculate_and_submit`); внутренние вызовы `calculate_tax` (prepare, auto-draft, submit) не дублируют `tax_calculate` через `contextvars`

### CIS UX & данные (продолжить)

- [x] Сущность **CISRecord** + **CISReviewTask** + **accountant_delegations** в **transactions-service** (Alembic + API).
- [x] **Модалка Confirm CIS** на странице **transactions** (Not CIS / verified with statement / self-attested + чекбоксы; привязка к txn).
- [x] **Tasks:** открытые CIS tasks на **транзакциях** (бейдж + Review); API `GET /cis/tasks`, scan, snooze.
- [x] **Напоминания:** поле `next_reminder_at` + `GET /cis/reminders/due`, snooze (push/cron — отдельно).
- [x] **Evidence pack:** `GET /cis/evidence-pack/manifest` (JSON + watermark text); **PDF/ZIP** — позже.

### HMRC submit / export

- [x] Двойной контур: tax-engine + integrations **unverified_cis_submit_acknowledged** (согласуйте тексты UX с юристом).
- [x] UI на **submission**: предупреждение + чекбокс перед submit, тело **`unverified_cis_submit_acknowledged`** на `/calculate-and-submit` при `cis_hmrc_submit_requires_unverified_ack`.
- [x] Привязка **confirmation_token** к **canonical hash** отчёта: `compute_quarterly_report_fingerprint` хэширует полный `HMRCMTDQuarterlyReport` (включая **`cis_disclosure`**). Тесты: `test_quarterly_report_fingerprint_includes_cis_disclosure`, `test_hmrc_mtd_submit_rejects_cis_disclosure_changed_after_confirm`.

### Accountant consult (максимальный план)

- [x] API **delegation** в transactions-service (`POST/GET /accountant/delegations`; **`can_submit_hmrc`** пока жёстко запрещён).
- [x] Статусы отчёта: draft → ready_for_accountant_review → accountant_reviewed → ready_for_user_confirm → submitted (**integrations-service** SQLite `workflow_status`; transition + latest API; confirm/submit enforcement; **tax-preparation** UI + demo «Mark accountant reviewed»).
- [x] MVP: **Accountant download link** (signed token `POST /cis/evidence-pack/share-token`, `GET /cis/evidence-pack/shared-zip?token=…`, HS256 с `INTERNAL_SERVICE_SECRET`; compliance **`cis_evidence_pack_shared_download`** при `COMPLIANCE_SERVICE_URL`); UI на **transactions** — копирование полного URL в буфер.
- [x] Billing: опционально консультация / SLA через **billing-service** — `GET /addons`, `POST /checkout/session` с `product: accountant_cis_consult` (Stripe `mode=payment`), webhook → кредиты сессий; `GET /subscription/{email}` → `accountant_consult_sessions_available`; `POST /internal/accountant-consult-session`; UI **my-subscription** + success/cancel pages.

### Чеклист доводки CIS variant B

- [ ] Юридически вычитать тексты (шаблоны: `apps/web-portal/pages/submission.tsx`, `transactions.tsx`; при необходимости — tax-preparation).
- [x] Контракт / E2E-слой: при `COMPLIANCE_SERVICE_URL` вызывается `post_audit_event` — тесты с моком: `test_cis_dismiss_sends_audit_when_compliance_configured` (transactions-service), `test_unverified_cis_ack_posts_compliance_audit` (integrations-service). Полный приём в **compliance-service** — см. его pytest.
- [x] Тесты pytest: маршруты `/cis/*`, `/accountant/*` в **transactions-service** (`tests/test_transactions_service_main.py`).
- [x] Виджет **To review — CIS** на **dashboard** (`pages/dashboard.tsx`) + деталь на **transactions**.
- [x] Выгрузка **ZIP** evidence pack: `GET /cis/evidence-pack/zip` (manifest JSON + NOTICE); кнопка на transactions. **PDF** с watermark — при необходимости отдельно.

### Уточнения продукта (зафиксировать в PRD)

- [ ] Submit в HMRC в v1: direct или только prepare + export?
- [ ] Бухгалтер: только read+comments или правки категорий без submit?
- [ ] Self-attested: отдельное подтверждение **каждый** final submit или одна master-attestation на tax year?

---

*Последнее обновление: 2026-04-17*
*Автор: MyNetTax Development Team*
