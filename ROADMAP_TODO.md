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
- [ ] Подготовить данные для ML модели (фаза 2)

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
- [ ] Промпт для ai-agent-service: "mortgage advisor" режим с контекстом юзера
- [ ] AI видит: доход, расходы, tax returns, инвойсы, deposit — даёт персонализированный ответ
- [ ] Примеры вопросов: "Can I get a mortgage?", "Czy mogę dostać kredyt hipoteczny?", "Чи можу я отримати іпотеку?"
- [ ] AI знает UK mortgage rules: income multiples, self-employed requirements, deposit minimums
- [ ] Fallback: если AI не уверен → "Рекомендуем поговорить с broker-ом" + ссылка на marketplace

### 1.5.2 Affordability Calculator
- [ ] Max mortgage по формулам: employed 4.5x, self-employed 3-4x (average 2-3 years)
- [ ] Расчёт по разным кредиторам: Barclays (1 год), HSBC (2 года), Halifax (retained profit)
- [ ] Monthly payment calculator: variable vs fixed, разные сроки (25/30/35 лет)
- [ ] Stress test: "Если ставка вырастет на 3%, ваш платёж будет £X" (HMRC требование)
- [ ] Stamp Duty calculator: first-time buyer relief, standard rates, surcharges
- [ ] Input: доход автоматически из данных MyNetTax (не вбивать руками)

### 1.5.3 Lender Comparison (реальные банки)
- [ ] База кредиторов с условиями для self-employed:
  - [ ] Barclays: 1 год accounts, 4.49x income, min 10% deposit
  - [ ] HSBC: 2 года accounts, 4x income, min 10% deposit
  - [ ] Halifax: 2 года, принимает retained profit для Ltd directors
  - [ ] Nationwide: 2 года SA302, 4.5x для strong applications
  - [ ] NatWest: 2 года, 4x, flex underwriting для contractors
  - [ ] Specialist: Kensington, Pepper Money, Together (adverse credit)
- [ ] Автоматический matching: профиль юзера → подходящие банки с % вероятности одобрения
- [ ] Фильтры: deposit %, income type, credit history, property type
- [ ] Обновление данных кредиторов каждый квартал

### 1.5.4 Document Auto-fill
- [ ] SA302 — уже генерируем через HMRC integration → автоприложить к mortgage pack
- [ ] Tax Year Overview — автозапрос через HMRC API
- [ ] Income & Expenditure form — автозаполнение из transactions-service
- [ ] Bank statements — экспорт из banking-connector за последние 6 месяцев
- [ ] Business accounts summary — из analytics-service (P&L за 2-3 года)
- [ ] Один клик → готовый пакет документов для broker-а

### 1.5.5 Broker Marketplace
- [ ] Партнёрство с 10-20 mortgage brokers специализирующихся на self-employed
- [ ] Broker получает: готовый mortgage pack + readiness score + income verification
- [ ] Юзер выбирает broker-а → бронирует консультацию (бесплатно для юзера)
- [ ] Revenue: £200-500 за квалифицированный лид (стандарт индустрии)
- [ ] Отзывы и рейтинги broker-ов от юзеров
- [ ] Фильтр: языки broker-а (EN, PL, RO, UA — для нашей аудитории мигрантов)

### 1.5.6 Mortgage Progress Tracker ("Дорога к ипотеке")
- [ ] Timeline с шагами от текущего состояния до подачи заявки:
  - Step 1: Build credit score (if needed)
  - Step 2: Save deposit (progress bar: £X of £Y saved)
  - Step 3: Complete 1-2 years self-employed accounts
  - Step 4: File tax return (SA302)
  - Step 5: Reduce outstanding debts
  - Step 6: Prepare mortgage pack
  - Step 7: Apply
- [ ] Автоматическое определение текущего шага из данных юзера
- [ ] Push-уведомления при достижении milestone: "🎉 Your deposit reached 10%!"
- [ ] Estimated timeline: "At your current savings rate, you'll be ready in 8 months"
- [ ] Monthly progress email: "Your mortgage readiness score improved from 62 to 71"

---

## Фаза 2: "Делает то, чего другие не умеют" (6-10 недель)

### 2.1 AI Tax Advisor на родном языке
- [ ] Fine-tune промпт для ai-agent-service с UK tax rules (NI, Income Tax bands, allowances)
- [ ] Добавить контекст пользователя: доход, расходы, категории → персонализированные советы
- [ ] Тестирование на 10 языках (английский, польский, румынский, украинский — приоритет)
- [ ] Примеры: "Могу ли я списать расходы на телефон?", "Сколько NI я заплачу?"

### 2.2 Voice input
- [ ] Интент-парсер: распознать "заплатил 50 фунтов за бензин" → {amount: 50, category: Fuel, currency: GBP}
- [ ] Поддержка 4 языков: EN, PL, RO, UK
- [ ] Интеграция с voice-gateway (STT уже есть)
- [ ] Мобильное приложение: кнопка микрофона на главном экране

### 2.3 MTD prep reminders (no auto-submit)
- [ ] Cron: за 3 дня до MTD дедлайна → автосбор данных из transactions и **черновик** quarterly report
- [ ] Уведомление: отчёт готов к review — пользователь **обязан** пройти draft → confirm → submit (как в `integrations-service`)
- [ ] **Не делать** фоновую/авто-подачу в HMRC (политика продукта: только после явного подтверждения)
- [ ] Audit: подготовка черновика, открытие self-check, confirm, submit

### 2.4 Real-time profit dashboard
- [ ] WebSocket endpoint: новая транзакция → push на дашборд
- [ ] Виджеты: "Profit today", "Profit this week", "Tax owed so far"
- [ ] Графики: доход vs расходы по неделям/месяцам
- [ ] Сравнение с прошлым годом

### 2.5 Tax savings tips
- [ ] База UK allowable expenses (home office £6/week, mileage 45p/mile, phone, insurance)
- [ ] Анализ транзакций юзера → персональные рекомендации
- [ ] "Вы не списали home office allowance — это £312/год экономии"
- [ ] Push-уведомление раз в месяц с суммой потенциальной экономии

### 2.6 Instant invoice payments
- [ ] Stripe Payment Links в каждом инвойсе
- [ ] Клиент получает email → нажимает "Pay now" → оплата картой
- [ ] Webhook: Stripe payment.succeeded → инвойс статус = "paid"
- [ ] Уведомление юзеру: "Invoice #INV-001 paid! £500 received"

---

## Фаза 3: "Viral growth" (10-16 недель)

### 3.1 Реферальная программа 2.0
- [ ] £25 credit за каждого приглашённого друга (обоим)
- [ ] Месяц Pro бесплатно для топ-10 рефереров каждый месяц
- [ ] Leaderboard в приложении (referral-service уже есть)
- [ ] Sharing: уникальная ссылка + QR код
- [ ] Email-кампания существующим юзерам: "Invite a friend, get £25"

### 3.2 Бесплатный MTD калькулятор (SEO-магнит)
- [ ] Лендинг: "UK Self-Employed Tax Calculator 2026"
- [ ] Без регистрации: ввёл доход → получил расчёт Income Tax + NI + take-home pay
- [ ] CTA: "Want to file automatically? Sign up free"
- [ ] SEO на 10 языках: "Kalkulator podatków UK" (польский), "Calculator impozit UK" (румынский)

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
- [ ] Free: 20 транзакций/мес, 1 банк, базовый дашборд, no MTD submission
- [ ] Starter £9: unlimited транзакции, MTD quarterly, 3 банка
- [ ] Growth £12: + invoice payments, AI advisor
- [ ] Pro £15: + voice input, auto-submission, priority support
- [ ] Business £25: + multi-business, accountant access, API

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
- [ ] Один аккаунт = несколько бизнесов (Uber + Etsy + freelance)
- [ ] Раздельный учёт доходов/расходов
- [ ] Объединённый tax report
- [ ] FreeAgent НЕ умеет — конкурентное преимущество

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

- [ ] Fail-fast **AUTH_SECRET_KEY** везде (нет дефолтов); preflight длина/энтропия секрета при старте в prod-профиле.
- [ ] Append-only audit + hash-chain по `user_id` (расширение **compliance-service** или отдельное хранилище).
- [x] **`CISAuditAction`** → `POST .../audit-events` из **transactions-service** (`crud_cis`, shared `post_audit_event`) при ключевых шагах.
- [x] Событие **`cis_unverified_submit_confirmed`** в compliance при ack на quarterly submit — **integrations-service** (если задан `COMPLIANCE_SERVICE_URL`).
- [ ] Писать audit из **documents-service** / **tax-engine** там, где UX ещё не прокинут.

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
- [ ] Статусы отчёта: draft → ready_for_accountant_review → accountant_reviewed → ready_for_user_confirm → submitted (UI + enforcement).
- [ ] MVP: кнопка **Request accountant review** + шаринг evidence pack (signed URLs, audit на скачивание).
- [ ] Billing: опционально консультация / SLA через **billing-service**.

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
