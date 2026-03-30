# SelfMonitor — Roadmap & Checklist

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
  - [ ] Создать 4 продукта: Starter £9, Growth £12, Pro £15, Business £25
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
- [ ] Заменить `allow_origins=["*"]` на домен в billing-service и других CORS конфигах
- [ ] Закрыть порты 5432, 6379, 8080 в firewall (оставить только 80, 443)
- [ ] Убрать `AUTH_BOOTSTRAP_ADMIN=true` после создания первого admin аккаунта

---

## Фаза 1: "Работает лучше всех" (4-6 недель)

### 1.1 Open Banking — автоимпорт транзакций из банков
- [ ] Зарегистрироваться на TrueLayer (https://truelayer.com) — бесплатный sandbox
- [ ] Заменить mock в banking-connector на TrueLayer API
- [ ] Реализовать OAuth2 flow: юзер авторизует банк → получаем access_token
- [ ] Автоимпорт транзакций за последние 90 дней
- [ ] Периодический sync каждые 4 часа (Celery task)
- [ ] UI: страница "Connect your bank" с логотипами банков
- [ ] Тестирование: sandbox → staging → production

### 1.2 Smart Auto-categorization
- [ ] Создать таблицу правил: merchant name → категория (Tesco → Groceries, Shell → Fuel)
- [ ] Добавить 200+ правил для UK (супермаркеты, заправки, Amazon, Uber)
- [ ] Fallback на categorization-service если правило не найдено
- [ ] UI: юзер может изменить категорию → система запоминает на будущее
- [ ] Подготовить данные для ML модели (фаза 2)

### 1.3 Receipt OCR
- [ ] Заменить LocalStack Textract mock на реальный AWS Textract
- [ ] Парсить: дата, сумма, merchant name, VAT amount
- [ ] Автосоздание транзакции из распознанного чека
- [ ] UI: кнопка "Scan receipt" → камера → результат
- [ ] Мобильное приложение: нативная камера через Expo

### 1.4 Push-уведомления о дедлайнах
- [ ] Email-уведомления: за 14, 7, 3, 1 день до MTD дедлайна
- [ ] Push (Expo Push Notifications) для мобильного приложения
- [ ] In-app banner на дашборде: "Quarterly submission due in 5 days"
- [ ] Auto-reminder если квартальная подача не сделана за 24 часа до дедлайна

### 1.5 Экспорт CSV/Excel
- [ ] Transactions → CSV/Excel с фильтрами (даты, категории)
- [ ] Invoices → CSV (список) + PDF (каждый инвойс)
- [ ] Tax report → PDF summary для бухгалтера
- [ ] HMRC-compatible format для Self Assessment

### 1.6 Мобильное приложение в App Store / Google Play
- [ ] Apple Developer Account ($99/год)
- [ ] Google Play Developer Account ($25 единоразово)
- [ ] `eas build --platform ios` + `eas build --platform android`
- [ ] App Store Connect: скриншоты, описание, privacy policy
- [ ] Google Play Console: listing, content rating
- [ ] Submit на review

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

### 2.3 Zero-click MTD
- [ ] Cron job: за 3 дня до MTD дедлайна → автосбор данных из transactions
- [ ] Автогенерация quarterly report
- [ ] Уведомление юзеру: "Ваш квартальный отчёт готов. Подтвердите или отредактируйте"
- [ ] Если юзер не ответил за 24 часа → авто-подача (с настройкой в профиле)
- [ ] Audit log каждого действия

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
- [ ] Embedded banking: открыть счёт прямо из SelfMonitor
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

*Последнее обновление: 2026-03-30*
*Автор: SelfMonitor Development Team*
