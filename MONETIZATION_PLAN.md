# SelfMonitor — Монетизация и выбор провайдеров

## 1. Open Banking провайдеры: полное сравнение

### Детальная таблица

| | **SaltEdge** | **Yapily** | **TrueLayer** | **Plaid** | **Finexer** |
|---|---|---|---|---|---|
| **Банков UK** | 150+ | 200+ | 100+ | 80+ | 50+ |
| **Банков глобально** | 1,586 (73 страны) | 2,000+ (19 стран EU) | 12 стран EU+UK | 12,000+ (US/EU/UK) | UK only |
| **Free tier** | 100 connections / 90 дней | Бесплатный sandbox | 500 connections бесплатно | 100 connections бесплатно | Бесплатный trial |
| **Старт продакшн** | ~$500/мес минимум | Usage-based, нет минимума | Enterprise-oriented | Pay-as-you-go | Стартап-дисконт |
| **~Цена за connection** | ~€0.10-0.15 (оценка) | ~£0.10-0.15 (enterprise) | ~£0.20-0.30 | ~$0.25-0.30 | Не раскрыта |
| **AIS (данные счёта)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PIS (платежи)** | ✅ | ✅ | ✅ (лучший UX) | ❌ | ✅ |
| **VRP (recurring)** | ✅ | ✅ (beta) | ✅ | ❌ | ❌ |
| **Data enrichment** | ✅ Категоризация транзакций | Ограниченно | ✅ | ✅ (лучший) | ❌ |
| **PSD2 compliant** | ✅ ISO 27001 | ✅ | ✅ | ✅ | ✅ |
| **Scraping (не-OB банки)** | ✅ Spectre (доп. покрытие) | ❌ | ❌ | ✅ | ❌ |
| **SDK/Docs качество** | Хорошее, REST v5/v6 | Хорошее | Отличное | Отличное | Среднее |
| **На 100K юзеров/мес** | ~£10-15K | ~£10-15K | ~£20-30K | ~£25-30K | Неизвестно |

### SaltEdge подробнее

**Плюсы:**
- Самое широкое покрытие банков глобально (1,586 банков, 73 страны) — важно если пользователи имеют счета в Польше, Румынии, Украине (не только UK)
- Spectre API — доступ к банкам БЕЗ Open Banking (через screen scraping) — покрывает банки которые не поддерживают OB API
- ISO 27001 сертификация — проще пройти compliance review
- Data enrichment из коробки — автокатегоризация транзакций (наша categorization-service может использовать)
- Partner Program — для стартапов без PSD2 лицензии, Salt Edge выступает как AISP

**Минусы:**
- Минимум ~$500/мес на продакшне — дороже Yapily для старта
- Free tier ограничен 90 днями и 100 connections — мало для тестирования
- Spectre (scraping) ≠ Open Banking — HMRC может не принять scraping как "digital records"
- API чуть старше по дизайну чем Yapily/TrueLayer
- UI consent screen менее кастомизируемый

**Когда SaltEdge лучший выбор:**
- Юзеры с банками НЕ в UK (Польша, Румыния — наша целевая аудитория мигрантов!)
- Нужно покрыть максимум банков с одним провайдером
- Нужна автокатегоризация транзакций из коробки

### Рекомендация по фазам

| Фаза | Юзеры | Провайдер | Стоимость/мес | Почему |
|---|---|---|---|---|
| **Старт** | 0-1K | **SaltEdge** sandbox + Partner | £0 → ~£500 | Покрывает UK + EU банки мигрантов. 90 дней бесплатно хватит на MVP тест |
| **Рост** | 1K-10K | **SaltEdge** production | ~£1-3K | Один провайдер для UK + Польша + Румыния. Data enrichment экономит dev время |
| **Масштаб** | 10K-50K | **SaltEdge + Yapily** | ~£5-10K | SaltEdge для EU банков, Yapily для UK (дешевле на объёме) |
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

| Тариф | Цена | Что включено | Целевая доля |
|---|---|---|---|
| **Free** | £0 | 20 транзакций/мес, 1 банк, дашборд, tax калькулятор | 40% |
| **Starter** | £9/мес | Unlimited транзакции, MTD quarterly, 3 банка, инвойсы (5/мес) | 30% |
| **Growth** | £12/мес | + invoice payments, AI advisor, receipt OCR, all банки | 15% |
| **Pro** | £15/мес | + voice input, auto-submission, priority support, CSV/Excel export | 10% |
| **Business** | £25/мес | + multi-business, accountant access, API, white-label инвойсы | 5% |

### 3.2 Дополнительные потоки revenue

| # | Поток | Модель | Revenue на 100K юзеров/мес |
|---|---|---|---|
| 1 | **Invoice instant payments** | 1% от суммы оплаченных инвойсов через Payment Links | £50-100K |
| 2 | **Marketplace commissions** | £5-50 за лид (страховка, пенсия, кредит) | £30-80K |
| 3 | **Accountant seats** | £3/мес за каждого клиента бухгалтера | £15-30K |
| 4 | **Premium AI add-on** | £3/мес (unlimited голосовые запросы, tax optimization) | £20-40K |
| 5 | **Banking referral** | £5-15 за открытие счёта через Tide/Starling | £10-20K |
| 6 | **Data insights (B2B)** | Анонимизированные тренды для banks/insurance (GDPR compliant) | £5-15K |

### 3.3 Unit Economics на 100K юзеров

```
REVENUE
───────────────────────────────────────
Subscriptions (60K платящих × £12.08 ARPU)    £725K/мес
Invoice payments (1% от £5-10M инвойсов)       £75K/мес
Marketplace commissions                         £50K/мес
Accountant seats (5K × £3)                      £15K/мес
Premium AI (12K × £3)                           £36K/мес
Banking referrals                               £15K/мес
───────────────────────────────────────
TOTAL REVENUE                                  £916K/мес  (£11M/год)


COSTS
───────────────────────────────────────
Infrastructure (AWS/DO)                         £20K/мес
Open Banking (SaltEdge + Yapily)                £15K/мес
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
Net Profit                                     £674K/мес  (£8.1M/год)
Margin                                         73.6%
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
