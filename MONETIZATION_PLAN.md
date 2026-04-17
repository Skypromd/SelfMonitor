# SelfMonitor — Монетизация и выбор провайдеров

## 1. Open Banking провайдеры: полное сравнение

### Детальная таблица

| | **SaltEdge** | **Yapily** | **TrueLayer** | **Plaid** | **Finexer** |
|---|---|---|---|---|---|
| **Банков UK** | 150+ | 200+ | 100+ | 80+ | 50+ |
| **Банков глобально** | 1,586 (73 страны) | 2,000+ (19 стран EU) | 12 стран EU+UK | 12,000+ (US/EU/UK) | UK only |
| **Free tier** | 100 connections / 90 дней | Бесплатный sandbox | 500 connections бесплатно | 100 connections бесплатно | Бесплатный trial |
| **Старт продакшн** | Usage-based (нет фикс. минимума) | Usage-based, нет минимума | Enterprise-oriented | Pay-as-you-go | Стартап-дисконт |
| **Модель оплаты** | За connection + refresh + PIS | За connection + refresh | За connection + payment | За connection | Не раскрыта |
| **AIS (данные счёта)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PIS (платежи)** | ✅ | ✅ | ✅ (лучший UX) | ❌ | ✅ |
| **VRP (recurring)** | ✅ | ✅ (beta) | ✅ | ❌ | ❌ |
| **Data enrichment** | ✅ Категоризация транзакций | Ограниченно | ✅ | ✅ (лучший) | ❌ |
| **PSD2 compliant** | ✅ ISO 27001 | ✅ | ✅ | ✅ | ✅ |
| **Scraping (не-OB банки)** | ✅ Spectre (доп. покрытие) | ❌ | ❌ | ✅ | ❌ |
| **SDK/Docs качество** | Хорошее, REST v5/v6 | Хорошее | Отличное | Отличное | Среднее |
| **На 100K юзеров/мес** | ~£12-20K (volume discount) | ~£10-15K | ~£20-30K | ~£25-30K | Неизвестно |

### SaltEdge подробнее

**Плюсы:**
- Самое широкое покрытие банков глобально (1,586 банков, 73 страны) — важно если пользователи имеют счета в Польше, Румынии, Украине (не только UK)
- Spectre API — доступ к банкам БЕЗ Open Banking (через screen scraping) — покрывает банки которые не поддерживают OB API
- ISO 27001 сертификация — проще пройти compliance review
- Data enrichment из коробки — автокатегоризация транзакций (наша categorization-service может использовать)
- Partner Program — для стартапов без PSD2 лицензии, Salt Edge выступает как AISP

**Ценообразование SaltEdge (usage-based):**

Цена зависит от количества обращений, не фиксированная. Три компонента:
- **Connection** — разовая плата за привязку банковского счёта
- **Refresh** — плата за каждое обновление данных (sync транзакций)
- **Payment Initiation (PIS)** — плата за каждый инициированный платёж

Чем больше объём — тем ниже цена за единицу (volume discounts):

| Юзеров | Connections/мес | Refreshes/мес (4×/день) | Примерная стоимость |
|---|---|---|---|
| 500 | 500 | 60K | ~£200-500 |
| 5K | 5K | 600K | ~£1-3K |
| 50K | 50K | 6M | ~£8-15K |
| 100K | 100K | 12M | ~£12-20K |

**Минусы:**
- Free tier ограничен 90 днями и 100 connections — мало для длительного тестирования
- Spectre (scraping) ≠ Open Banking — HMRC может не принять scraping как "digital records"
- API чуть старше по дизайну чем Yapily/TrueLayer
- UI consent screen менее кастомизируемый
- Точная цена только через sales — нет публичного прайса

**Когда SaltEdge лучший выбор:**
- Юзеры с банками НЕ в UK (Польша, Румыния — наша целевая аудитория мигрантов!)
- Нужно покрыть максимум банков с одним провайдером
- Нужна автокатегоризация транзакций из коробки

### Рекомендация по фазам

| Фаза | Юзеры | Провайдер | Стоимость/мес | Почему |
|---|---|---|---|---|
| **Старт** | 0-1K | **SaltEdge** sandbox + Partner | £0 → ~£200-500 | Покрывает UK + EU банки мигрантов. Usage-based = платишь только за реальных юзеров |
| **Рост** | 1K-10K | **SaltEdge** production | ~£1-3K | Один провайдер для UK + Польша + Румыния. Data enrichment экономит dev время |
| **Масштаб** | 10K-50K | **SaltEdge + Yapily** | ~£5-12K | SaltEdge для EU банков, Yapily для UK (дешевле refreshes на объёме) |
| **Enterprise** | 50K-100K | **Yapily (UK)** + **SaltEdge (EU)** + **TrueLayer (payments)** | ~£15-25K | Оптимальная комбинация: цена + покрытие + instant payments |
| **100K+** | Прямая интеграция OBIE | ~£5-10K | Убрать посредника для топ-5 UK банков (Barclays, HSBC, Lloyds, NatWest, Santander) |

**Ключевой инсайт для SelfMonitor**: SaltEdge — лучший старт именно для нас потому что наша ниша — мигранты. У поляка в UK есть счёт в Barclays И в PKO Bank Polski. Ни Yapily, ни TrueLayer не покрывают польские банки. SaltEdge покрывает.

---

## 2. Payment провайдеры

### Сравнение на объёме

| | **Stripe** | **GoCardless** | **Adyen** |
|---|---|---|---|
| **Модель** | 1.5% + 20p (UK card) | 1% + capped £4 (Direct Debit) | Interchange++ (~0.6-0.9%) |
| **Подписка £9/мес** | £0.34 (3.7%) | £0.09 (1%) | ~£0.07 (0.8%) |
| **Подписка £25/мес** | £0.58 (2.3%) | £0.25 (1%) | ~£0.17 (0.7%) |
| **На 60K платящих юзеров** | ~£18.5K/мес | ~£6.5K/мес | ~£5K/мес |
| **Карты** | ✅ | ❌ (только DD) | ✅ |
| **Direct Debit** | ✅ (через Stripe DD) | ✅ (core product) | ✅ |
| **Invoice payments** | ✅ Payment Links | ❌ | ✅ |
| **Chargeback fee** | £20 | £0 (DD не имеет chargebacks) | €12 |
| **Setup** | 0 — уже интегрирован | 1-2 дня | 1-2 недели + минимум €120/мес |
| **Billing portal** | ✅ Встроенный | ❌ Нужен свой | ✅ |

### Рекомендация

| Фаза | Провайдер | Экономия vs Stripe only |
|---|---|---|
| **0-5K юзеров** | **Stripe** (уже работает) | — |
| **5K-50K** | **GoCardless** (подписки) + **Stripe** (инвойсы) | ~£8-12K/мес |
| **50K-100K** | **GoCardless** (80% юзеров DD) + **Stripe** (20% карты + инвойсы) | ~£12-15K/мес |

---

## 3. Модель монетизации

### 3.1 Тарифные планы

Цены ниже — **без VAT** на кассе (UK VAT применяется в checkout при необходимости). Фокус продукта: **CIS subcontractors** (statements, verified vs self-attested, refund narrative) + MTD ITSA. Лимиты и флаги в коде: `auth-service` → `PLAN_FEATURES`, JWT, `libs/shared_auth/plan_limits.py`.

| Тариф | Цена | Лимиты (кратко) | MTD / VAT / CIS | Целевая доля |
|---|---|---|---|---|
| **Free** | £0 | 1 банк, 0 sync/день, 200 tx/мес | Калькулятор; без HMRC submit | 40% |
| **Starter** | **£12**/мес | 1 банк, **1** sync/день, 500 tx, **~90 дней** истории | **Guided** MTD submit; **CIS refund tracker**; без direct+fraud strict; без VAT | 30% |
| **Growth** | **£15**/мес | 2 банка, **3** sync/день, 2k tx, **12 мес** истории | Guided MTD; CIS; evidence basic (продукт); без VAT | 15% |
| **Pro** | **£18**/мес | **5** банков, **10** sync/день, 5k tx, **24 мес** | **Direct-style** submit + полный **client_context**; **VAT** returns; 1 accountant review credit/мес | 10% |
| **Business** | **£28**/мес | **10** банков, **25** sync/день, высокий объём, **36 мес** | Как Pro + **4** review credits/мес; white-label | 5% |

Позиционирование: refund и обязательства CIS — **оценки (estimate)**, не гарантия; подача в HMRC — **подготовка и submit после явного подтверждения**, без фоновой авто-подачи.

### 3.2 Дополнительные потоки revenue

| # | Поток | Модель | Revenue на 100K юзеров/мес |
|---|---|---|---|
| 1 | **Invoice instant payments** | 1% от суммы оплаченных инвойсов через Payment Links | £50-100K |
| 2 | **Mortgage broker leads** | £200-500 за квалифицированный лид (готовый pack + score) | £60-150K |
| 3 | **Marketplace commissions** | £5-50 за лид (страховка, пенсия, кредит) | £30-80K |
| 4 | **Accountant seats** | £3/мес за каждого клиента бухгалтера | £15-30K |
| 5 | **Premium AI add-on** | £3/мес (AI mortgage advisor + tax advisor + voice) | £20-40K |
| 6 | **Banking referral** | £5-15 за открытие счёта через Tide/Starling | £10-20K |
| 7 | **Data insights (B2B)** | Анонимизированные тренды для banks/insurance (GDPR compliant) | £5-15K |

#### Mortgage broker leads — подробный расчёт

```
100K юзеров
  → 30% self-employed с целью купить жильё в ближайшие 2 года = 30K
  → 10% из них используют mortgage advisor в месяц = 3K
  → 40% получают readiness score "ready" или "almost ready" = 1,200
  → 25% нажимают "Connect with broker" = 300 лидов/мес
  → £200-500 за лид (стандарт mortgage industry)
  = £60-150K/мес дополнительного revenue

Для сравнения: средний mortgage в UK = £290K.
Broker получает 0.3-0.5% = £870-1,450 комиссии.
£200-500 за лид — справедливая цена для broker-а.
```

### 3.3 Unit Economics на 100K юзеров

```
REVENUE
───────────────────────────────────────
Subscriptions (60K платящих × £12.08 ARPU)    £725K/мес
Mortgage broker leads (300 × £350 avg)        £105K/мес
Invoice payments (1% от £5-10M инвойсов)       £75K/мес
Marketplace commissions                         £50K/мес
Premium AI + mortgage advisor (12K × £3)        £36K/мес
Accountant seats (5K × £3)                      £15K/мес
Banking referrals                               £15K/мес
───────────────────────────────────────
TOTAL REVENUE                                £1,021K/мес  (£12.3M/год)


COSTS
───────────────────────────────────────
Infrastructure (AWS/DO)                         £20K/мес
  Open Banking (SaltEdge + Yapily, usage-based)    £15K/мес
Payments (GoCardless + Stripe)                  £10K/мес
OpenAI API (AI advisor + voice)                  £8K/мес
AWS Textract (OCR)                               £3K/мес
SMTP (email notifications)                       £1K/мес
───────────────────────────────────────
Tech costs                                      £57K/мес

Support team (8 человек)                        £30K/мес
Engineering (12 человек)                        £90K/мес
Marketing                                       £50K/мес
Office / legal / admin                          £15K/мес
───────────────────────────────────────
People + overhead                              £185K/мес

TOTAL COSTS                                    £242K/мес


PROFIT
═══════════════════════════════════════
Net Profit                                     £779K/мес  (£9.3M/год)
Margin                                         76.3%
```

### 3.4 Путь к 100K юзеров

| Период | Юзеры | Платящие | MRR | Ключевое действие |
|---|---|---|---|---|
| **Мес 1-2** | 500 | 150 | £1.5K | Запуск. Facebook groups диаспор (PL, RO, UA). HMRC recognition |
| **Мес 3-4** | 2K | 700 | £7K | App Store + Google Play. Реферальная программа (£25 за друга) |
| **Мес 5-6** | 5K | 2K | £20K | SEO контент на 10 языках. Accountant partnerships (первые 50) |
| **Мес 7-9** | 15K | 6K | £65K | GoCardless для DD. MTD deadline pressure (Oct 2026 = Q2 deadline) |
| **Мес 10-12** | 30K | 13K | £140K | **Seed round £500K-1M** (при 10x ARR multiple). Hire sales team |
| **Мес 13-18** | 60K | 28K | £310K | Marketplace launch. TrueLayer payments. Enterprise features |
| **Мес 19-24** | 100K | 60K | £725K | **Series A ready** (£5-10M при 15x ARR = £130M+ valuation) |

### 3.5 Конверсия Free → Paid

Стратегия "value wall" — Free юзер получает ценность, но упирается в лимит:

| Триггер | Free лимит | Upgrade мотивация |
|---|---|---|
| Транзакции | 20/мес | "You've imported 20 transactions. Upgrade for unlimited" |
| MTD submission | Нельзя | "File your quarterly return — upgrade to Starter" |
| Банки | 1 банк | "Connect all your banks — upgrade to Starter" |
| Инвойсы | Нельзя | "Send professional invoices — upgrade to Starter" |
| AI advisor | 3 вопроса/мес | "Unlimited tax advice — upgrade to Growth" |
| Receipt OCR | 5/мес | "Scan unlimited receipts — upgrade to Growth" |

Ожидаемая конверсия: **25-35% за первый год** (индустрия SaaS freemium: 2-5%, но MTD — законодательное требование, не опция).

---

## 4. Сравнение с конкурентами по цене

| Фича | SelfMonitor £9 | FreeAgent £19 | QuickBooks £10 | Xero £16 |
|---|---|---|---|---|
| MTD quarterly | ✅ | ✅ | ✅ | ✅ |
| Final declaration | ✅ | ✅ | ✅ | ✅ |
| Bank connections | 3 | Unlimited | 1 | Unlimited |
| Инвойсы | 5/мес | Unlimited | 20/мес | 20/мес |
| Receipt OCR | ❌ (Growth) | ✅ | ✅ | ❌ (add-on) |
| AI advisor | ❌ (Growth) | ❌ | ❌ | ❌ |
| Мультиязычность | ✅ 10 языков | ❌ English only | ❌ English only | ❌ English only |
| Voice input | ❌ (Pro) | ❌ | ❌ | ❌ |
| Auto-submission | ❌ (Pro) | ❌ | ❌ | ❌ |
| Mobile app | ✅ | ✅ | ✅ | ✅ |

**Вывод**: На £9/мес даём 80% того что FreeAgent за £19. На £15/мес (Pro) — даём ВСЁ что FreeAgent + AI + voice + auto-submission чего у них нет.

---

*Последнее обновление: 2026-03-30*
