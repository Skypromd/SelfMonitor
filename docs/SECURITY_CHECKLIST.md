# Чеклист безопасности перед релизом

## Секреты и конфигурация

- [ ] Нет секретов в репозитории; `.env` в `.gitignore`.
- [ ] Прод: секреты из vault/Secret Manager; ротация ключей JWT и HMRC OAuth по runbook.
- [ ] `AUTH_SECRET_KEY` и Stripe ключи различаются по окружениям.

## Сеть и доступ

- [ ] CORS в проде ограничен известными origin (не `*` для креденшелов).
- [ ] Rate limiting на gateway или edge (Cloudflare/nginx) для публичных маршрутов.
- [ ] Внутренние сервисы не торчат в интернет без gateway.

## Данные

- [ ] БД и объектное хранилище: шифрование at-rest (провайдер).
- [ ] Политика retention документов согласована и задокументирована.
- [ ] Резервное копирование и тест восстановления (см. ops runbook).

## Приложение

- [ ] Зависимости: `pip-audit` / аналог в CI (частично есть в workflow).
- [ ] Образы: скан уязвимостей (Trivy и т.д.).
- [ ] HMRC: `HMRC_REQUIRE_EXPLICIT_CONFIRM=true` в проде; см. `docs/POLICY_SPEC.md`.

## Наблюдаемость

- [ ] Алерты на 5xx, рост латентности, failed OCR, failed HMRC submit.
- [ ] Correlation / request id через gateway (по мере внедрения).
