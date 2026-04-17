# Планы и фичи (синхрон с `auth-service`)

Источник правды в коде: `services/auth-service/app/main.py` → **`PLAN_FEATURES`**.  
JWT при логине получает лимиты и флаги (`libs/shared_auth/plan_limits.py`).

Публичный прайс: `apps/web-portal/components/LandingPage.tsx` и `GET /subscription/plans` — **Starter £12, Growth £15, Pro £18, Business £28** (ex VAT).

| Plan | £/mo | Bank | Sync/day | History (mo) | Tx/mo | GB | HMRC guided | HMRC direct+fraud | VAT | CIS tracker | Acct. reviews/mo |
|------|------|------|----------|--------------|-------|-----|-------------|-------------------|-----|-------------|------------------|
| free | 0 | 1 | 0 | 3 | 200 | 1 | no | no | no | no | 0 |
| starter | 12 | 1 | 1 | 3 | 500 | 2 | yes | no | no | yes | 0 |
| growth | 15 | 2 | 3 | 12 | 2000 | 6 | yes | no | no | yes | 0 |
| pro | 18 | 5 | 10 | 24 | 5000 | 10 | yes | yes | yes | yes | 1 |
| business | 28 | 10 | 25 | 36 | high | 25 | yes | yes | yes | yes | 4 |

Остальные колонки (AI cat., OCR, mortgage, API, white-label) — без изменений по сравнению с предыдущей матрицей; см. `PLAN_FEATURES` в коде.
