# Monorepo Project

Этот репозиторий содержит полный код для проекта, как описано в архитектурном документе.

## Структура репозитория

- **/apps**: Фронтенд-приложения (веб и mobile web).
- **/services**: Бэкенд-микросервисы на Python (FastAPI).
- **/libs**: Общие библиотеки и модули (DTO, утилиты для БД).
- **/infra**: Код инфраструктуры (Terraform, Kubernetes).
- **/ml**: Модели машинного обучения и скрипты для их обслуживания.
- **/tools**: Вспомогательные скрипты для разработки.
- **/docs**: Документация проекта (PRD, DPIA).
- **/.github**: Конфигурации для CI/CD (GitHub Actions).

## Быстрый старт (с Docker Compose)

Самый простой способ запустить весь проект локально — использовать Docker Compose.

1. **Подготовьте переменные окружения:**
   В корне проекта создайте `.env` из шаблона:

   ```bash
   cp .env.example .env
   ```

   При необходимости обновите значения в `.env` (секреты и URL).

2. **Запустите бэкенд:**
   Из корневой директории проекта выполните команду:

   ```bash
   cp .env.example .env
   docker-compose up --build
   ```

   Перед запуском заполните секреты в `.env` (JWT secret, DB password, Vault/Weaviate credentials). Эта команда соберёт образы для всех сервисов и запустит их вместе с базой данных PostgreSQL. Backend-сервисы будут доступны по адресам `http://localhost:8000`, `http://localhost:8001` и так далее.

3. **Запустите фронтенд:**
   В **новом окне терминала** перейдите в директорию веб-портала и запустите его:

   ```bash
   cd apps/web-portal
   npm install
   npm run dev
   ```

4. **Откройте приложение:**
   Откройте в браузере `http://localhost:3000`. Вы должны увидеть страницу регистрации/входа.

## Поддержка устройств (web-only)

Текущий формат продукта — **web-only**:

- доступен на ноутбуке/ПК через браузер;
- доступен на телефоне через мобильный браузер;
- отдельного нативного приложения для iOS/Android пока нет.

> Обновление: начата реализация нативного mobile shell в `apps/mobile` (Expo + WebView),
> чтобы выпустить приложение в App Store / Google Play с максимальным переиспользованием веб-версии.

## Запуск отдельных сервисов

Каждый сервис в директории `services` является независимым приложением. Для запуска отдельного сервиса:

1. Перейдите в директорию сервиса, например, `cd services/auth-service`.
2. Установите зависимости: `pip install -r requirements.txt`.
3. Запустите сервер: `uvicorn app.main:app --reload`.

Для получения дополнительной информации обратитесь к `README.md` внутри каждого сервиса.

## Запуск mobile-приложения (in progress)

```bash
cd apps/mobile
npm install
cp .env.example .env
npm run start
```

Детали и roadmap: `apps/mobile/README.md`.

## Тестирование

Каждый сервис должен содержать свои собственные тесты в директории `tests/`. Тесты написаны с использованием `pytest`.

Чтобы запустить тесты для конкретного сервиса:

1. Перейдите в директорию сервиса, например, `cd services/auth-service`.
2. Убедитесь, что установлены зависимости для тестирования (они включены в `requirements.txt`).
3. Запустите pytest: `pytest`.

CI-пайплайн, настроенный в `.github/workflows/ci.yaml`, также автоматически запускает эти тесты при внесении изменений.

## Release readiness

Перед релизом рекомендуется выполнить preflight-проверки из корня репозитория:

```bash
python3 tools/release_preflight.py --quick
```

Для расширенной проверки с фронтенд-сборкой:

```bash
python3 tools/release_preflight.py --include-frontend
```

Для фиксации baseline по времени выполнения критических проверок:

```bash
python3 tools/release_preflight.py --quick --include-frontend \
  --timings-json docs/observability/baselines/preflight_quick_YYYY-MM-DD.json
```

См. также: `docs/observability/PERFORMANCE_BASELINE.md`.

Операционные инструкции:

- `docs/release/GO_LIVE_RUNBOOK.md`
- `docs/release/ROLLBACK_DRILL.md`
