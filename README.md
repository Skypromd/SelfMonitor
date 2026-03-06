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

## Changelog

### 2026-03-06

#### Новые сервисы

| Сервис | Порт | Описание |
|---|---|---|
| `services/finops-monitor` | 8021 | Мониторинг финансовых операций, отслеживание MTD/ITSA |
| `services/mtd-agent` | 8022 | Агент для автоматической подачи MTD-деклараций в HMRC |
| `services/voice-gateway` | 8023 | Голосовой шлюз (STT/TTS, WebSocket) |
| `services/ai-agent-service` | 80 | SelfMate AI агент с памятью, инструментами и многоязычной поддержкой |

#### Исправления тестов (37/37 ✅)

- **ai-agent-service** (17/17): исправлены `AsyncMock` в conftest, защита от `ZeroDivisionError` в `_update_performance_metrics`, mock Redis в тесте профиля
- **mtd-agent** (10/10): пустая строка API-ключа теперь трактуется как «нет ключа», добавлена ветка `else` в `_determine_actions` для >30 дней
- **voice-gateway** (10/10): все тесты прошли с первого запуска

#### Конфигурация spell-check

- `cspell.json` расширен: ~250 технических слов в `words`, кириллические `.md`-файлы и demo-скрипты добавлены в `ignorePaths`
- Результат: **0 ошибок** по всему workspace

#### Коммиты

| Хэш | Описание |
|---|---|
| `dc33d9e` | feat: MTD Agent, Voice Gateway, SelfMate Redis refactor, multi-language support |
| `3a0a8b3` | fix: resolve test failures across ai-agent-service, mtd-agent, voice-gateway |
| `0bc9b79` | fix: repair cspell.json invalid JSON (duplicate block appended) |
| `357c73b` | fix: restore 0 cspell errors — add 40 new words, ignore Cyrillic MD and demo files |

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
