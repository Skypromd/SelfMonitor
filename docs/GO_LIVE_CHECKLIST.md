# Go Live checklist (день релиза)

Использовать перед первым прод‑трафиком или крупным релизом. Детали — в ссылках.

## За 48 часов

- [ ] **Scope:** согласован **`docs/production-scope.md`**, команда понимает **`docs/non-goals.md`**.
- [ ] **Секреты:** в Secret Manager / vault; нет утечек в git (gitleaks в CI зелёный).
- [ ] **Stripe:** live ключи, **webhook secret**, URL webhook доступен по HTTPS; тестовое событие в Dashboard.
- [ ] **HMRC:** sandbox/prod env, **`HMRC_REQUIRE_EXPLICIT_CONFIRM=true`** в prod; runbook прочитан.
- [ ] **Бэкап:** последний снимок БД + политика RPO; **`docs/runbooks/restore-db.md`** под рукой.

## За 24 часа

- [ ] **Staging:** тот же compose/k8s профиль, что prod (урезанные ресурсы допустимы); smoke **`scripts/smoke_gateway_health.*`** зелёный.
- [ ] **Миграции:** применены на staging; план на prod — отдельный job / helm hook.
- [ ] **Алерты:** gateway 5xx, billing errors, DB, очередь OCR (если используется).
- [ ] **Rollback:** кто нажимает, какой тег образа откатываем — **`docs/runbooks/rollback.md`**.

## В день релиза

- [ ] Версии образов / git tag зафиксированы.
- [ ] Миграции prod — OK.
- [ ] Smoke prod: health через gateway, один логин, один критичный путь (импорт / документ / биллинг по выбору).
- [ ] Статус‑страница или внутренний канал «релиз идёт / готово».

## После релиза (24–72 ч)

- [ ] Мониторинг error rate / p95; нет всплеска 401/403 на auth.
- [ ] Логи: выборочно **нет** сырого PII.
- [ ] Postmortem шаблон готов, если был инцидент — **`docs/runbooks/incident-triage.md`**.

## Ссылки

- **`docs/SECURITY_CHECKLIST.md`**
- **`docs/POLICY_SPEC.md`**
- **`docs/TODO_PRODUCTION.md`**
