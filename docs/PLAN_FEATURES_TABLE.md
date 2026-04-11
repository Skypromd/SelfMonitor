# Планы и фичи (синхрон с `auth-service`)

Источник правды в коде: `services/auth-service/app/main.py` → **`PLAN_FEATURES`**.  
JWT при логине получает числовые лимиты и (для новых токенов) булевы флаги; при отсутствии флагов сервисы могут выводить их из поля **`plan`** (см. `libs/shared_auth/plan_limits.py`).

| Plan | Bank conn. | Tx / month | Storage GB | AI cat. | OCR | Cash-flow fcst. | Tax calc. | HMRC submit | Smart search | Mortgage | Adv. analytics | API | Team members | White-label |
|------|------------|------------|------------|---------|-----|-----------------|-----------|-------------|--------------|----------|----------------|-----|--------------|-------------|
| free | 1 | 200 | 1 | no | no | no | basic | no | no | no | no | no | 1 | no |
| starter | 1 | 500 | 2 | yes | yes | yes | full | no | no | no | no | no | 1 | no |
| growth | 2 | 2000 | 6 | yes | yes | yes | full | no | no | no | no | no | 1 | no |
| pro | 3 | 5000 | 10 | yes | yes | yes | full | yes | yes | yes | yes | yes | 1 | no |
| business | 5 |999999 | 25 | yes | yes | yes | full | yes | yes | yes | yes | yes | 1 | yes |

Публичный прайс на лендинге: `apps/web-portal/components/LandingPage.tsx` — суммы и формулировки должны совпадать с этой таблицей и политикой «одна подписка = один пользователь».
