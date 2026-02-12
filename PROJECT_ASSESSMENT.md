# ОЦЕНКА ПРОЕКТА: FinTech Platform

**Дата оценки:** 2026-02-12
**Автор:** Автоматический аудит кодовой базы

---

## ОБЩЕЕ РЕЗЮМЕ

Проект представляет собой **масштабный прототип** микросервисной FinTech-платформы для самозанятых, написанный на Python (FastAPI) + Next.js (TypeScript). По масштабу и охвату — это впечатляющая работа, покрывающая полный спектр от бэкенда до инфраструктуры. Однако код содержит ряд **критических дефектов**, которые не позволяют считать его production-ready, несмотря на заявления в `PROJECT_DOSSIER.md`.

### Итоговая оценка: 4.5 / 10

| Критерий                  | Оценка (1-10) | Комментарий                                              |
|---------------------------|:-------------:|----------------------------------------------------------|
| Архитектурное видение     | 8             | Отличный замысел, широкий охват                          |
| Качество кода (Backend)   | 5             | Рабочий, но с серьёзными упрощениями                     |
| Качество кода (Frontend)  | 2             | **Критический дефект:** дублирование всего кода           |
| Безопасность              | 3             | Архитектура хорошая, реализация — заглушки               |
| Тестирование              | 5             | Хорошая основа, но покрытие неполное                     |
| Инфраструктура / DevOps   | 6             | Docker Compose отличный, Terraform/K8s — заглушки        |
| ML / Data Science         | 2             | Полностью имитация, нет реального кода                   |
| Документация              | 7             | Обширная, но содержит дубли                              |
| Готовность к продакшену   | 2             | Множество критических проблем                            |

---

## 1. КРИТИЧЕСКИЕ ПРОБЛЕМЫ (BLOCKERS)

### 1.1. Фронтенд: Массовое дублирование кода

**Серьёзность: КРИТИЧЕСКАЯ**

Практически каждый файл в `apps/web-portal/pages/` содержит **полное дублирование своего содержимого** — код повторяется дважды внутри одного файла. Примеры:

- `pages/index.tsx` — **806 строк**, из которых ~400 — дублированный код. Файл содержит два объявления `export default function HomePage()`, два объявления `DocumentsManager`, два `TaxCalculator`. **Этот файл не скомпилируется.**
- `pages/dashboard.tsx` — **298 строк**, содержит два объявления `TaxCalculator`, два `CashFlowChart`, два `ActionCenter`, два `export default function DashboardPage`. **Не скомпилируется.**
- `pages/_app.tsx` — **150 строк**, содержит два `AppContent`, два `MyApp`, два `export default MyApp`. **Не скомпилируется.**

Вердикт: **Фронтенд-приложение неработоспособно** — оно не пройдёт компиляцию TypeScript и Next.js.

### 1.2. Аутентификация: `fake_auth_check` повсюду

**Серьёзность: КРИТИЧЕСКАЯ**

В **12 из 16 бэкенд-сервисов** аутентификация реализована через заглушку:

```python
def fake_auth_check() -> str:
    return "fake-user-123"
```

Только `auth-service` имеет реальную JWT-аутентификацию, но **ни один другой сервис не валидирует токены**. Это означает:
- Любой может получить доступ к любым данным любого пользователя
- Все данные привязаны к `"fake-user-123"` — мультитенантность невозможна
- API Gateway (nginx) не проверяет авторизацию

### 1.3. Auth-service: In-memory хранилище пользователей

**Серьёзность: КРИТИЧЕСКАЯ**

Auth-service хранит пользователей в dict `fake_users_db` — обычном Python-словаре в памяти процесса. При каждом перезапуске контейнера все пользователи теряются. Это единственный сервис, не подключённый к БД (PostgreSQL), хотя остальные используют Alembic и SQLAlchemy.

### 1.4. Registration endpoint использует OAuth2PasswordRequestForm

**Серьёзность: ВЫСОКАЯ**

```python
@app.post("/register", response_model=User)
async def register(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
```

Регистрация принимает `OAuth2PasswordRequestForm` (поле `username`), а не кастомную модель с полем `email`. При этом фронтенд отправляет JSON `{ email, password }`, что несовместимо с `OAuth2PasswordRequestForm`, ожидающим `application/x-www-form-urlencoded`. **Регистрация с фронтенда не работает.**

---

## 2. СЕРЬЁЗНЫЕ ПРОБЛЕМЫ

### 2.1. Документация с дубликатами

Файл `docs/security/security_overview_2025-10-04.md` содержит контент, повторённый дважды (строки 1-53 и 54-102). Это тот же паттерн дублирования, что и во фронтенде.

### 2.2. CI/CD пайплайн неактивен

`ci.yaml` содержит закомментированную команду `pytest`:
```yaml
    - name: Run tests with pytest
      run: |
        echo "Pytest would run here if 'tests/' directory existed."
        # pytest
```

Тесты **фактически не запускаются в CI**. При этом у 7 сервисов есть тесты — но пайплайн обрабатывает только 3 из них (`auth-service`, `transactions-service`, `documents-service`).

### 2.3. Отсутствие Dockerfile для nginx

В `docker-compose.yml` nginx указан с `build: ./nginx`, но в директории `/workspace/nginx/` есть только `nginx.conf` и **нет Dockerfile**. Docker Compose не сможет собрать этот сервис.

### 2.4. Зависимости без версий

Все `requirements.txt` указывают зависимости **без версий**:
```
fastapi
uvicorn[standard]
pydantic[email]
```

Это классический антипаттерн, приводящий к непредсказуемым билдам — каждая сборка может получить разные версии библиотек.

### 2.5. `datetime.datetime.utcnow()` — устаревший метод

В `analytics-service` используется:
```python
created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
```

`utcnow()` является deprecated в Python 3.12 (целевая версия проекта). Нужно использовать `datetime.datetime.now(datetime.UTC)`.

### 2.6. Секреты в docker-compose.yml

Пароли, токены и секретные ключи хранятся в открытом виде:
```yaml
POSTGRES_PASSWORD: password
AUTH_SECRET_KEY: "a_secure_random_string_for_jwt_signing_!@#$%^"
VAULT_TOKEN: "dev-root-token"
```

Для локальной разработки это допустимо, но необходим `.env` файл или Docker secrets для любого другого окружения.

---

## 3. УМЕРЕННЫЕ ПРОБЛЕМЫ

### 3.1. Mobile app — пустая заглушка

`apps/mobile/` содержит только `package.json` и `.gitkeep`. В PROJECT_DOSSIER заявлена поддержка мобильных приложений, но фактически код отсутствует.

### 3.2. ML — полностью имитация

`ml/models/train.py` — это плейсхолдер:
```python
accuracy = 0.95 # Simulated accuracy
print("Model artifact was not saved (simulation).")
```

Реальные sklearn-импорты закомментированы. Categorization-service использует rule-based подход, не ML-модель.

### 3.3. Terraform — минимальная заготовка

`infra/terraform/main.tf` содержит только один ресурс (S3 bucket) с закомментированным backend. Kubernetes-директория (`infra/k8s/`) пуста.

### 3.4. OpenTelemetry-инструментация неполная

Только `tax-engine` и `transactions-service` настроены с OpenTelemetry. В `auth-service` используется Prometheus instrumentator, но у остальных 13 сервисов нет никакой инструментации.

### 3.5. Inter-service communication без retry и circuit breaker

Все межсервисные вызовы через `httpx` используют простой try/except без retry-логики, circuit breaker или dead-letter queue:
```python
except httpx.RequestError as e:
    print(f"Error: Could not log audit event: {e}")
```

### 3.6. Shared libraries не используются

`libs/common-types/pydantic_models.py` определяет `SharedUser`, но ни один сервис его не импортирует. `libs/clients/python/transactions_client/__init__.py` содержит лишь комментарий "auto-generated, do not edit". Shared library система не интегрирована.

### 3.7. OpenAPI спецификации могут быть устаревшими

Файлы `openapi.yaml` существуют во многих сервисах, но неясно, синхронизированы ли они с реальными эндпоинтами.

---

## 4. СИЛЬНЫЕ СТОРОНЫ

Несмотря на перечисленные проблемы, проект демонстрирует ряд значительных достижений:

### 4.1. Архитектурная целостность

Микросервисная архитектура из 16 сервисов логично структурирована:
- **auth-service** — аутентификация, 2FA (TOTP), ролевая модель
- **user-profile-service** — профили с Alembic-миграциями
- **transactions-service** — транзакции с автоматической категоризацией
- **banking-connector** — Open Banking + Celery для фоновых задач
- **documents-service** — загрузка в S3 + OCR через Celery worker
- **qna-service** — векторный поиск через Weaviate + SentenceTransformers
- **tax-engine** — расчёт налогов с OpenTelemetry-трейсингом
- **compliance-service** — immutable audit log
- И другие...

### 4.2. Качественный Docker Compose

`docker-compose.yml` на 382 строки — это отличная конфигурация, включающая:
- 16 приложений + PostgreSQL, Redis, Weaviate, LocalStack, Vault
- Prometheus + Grafana + Loki + Promtail + Jaeger
- Celery workers для фоновых задач
- Init-скрипт для создания баз данных
- AWS CLI для создания S3 bucket

### 4.3. Асинхронная обработка

Celery + Redis используются для:
- Импорта банковских транзакций (banking-connector -> celery-worker -> transactions-service)
- OCR-обработки документов (documents-service -> celery-worker-docs -> qna-service)

Это правильный подход к обработке долгих операций.

### 4.4. Observability стек

Полный стек наблюдаемости:
- **Метрики:** Prometheus + Grafana (с преднастроенными дашбордами)
- **Логи:** Loki + Promtail
- **Трейсинг:** Jaeger + OpenTelemetry

### 4.5. Тестирование — хорошая основа

- **Unit-тесты:** 7 сервисов имеют тесты (auth, transactions, compliance, consent, tax-engine, banking-connector, user-profile)
- **Contract-тесты (Pact):** Есть пример для пары TaxEngine <-> Transactions
- **Integration-тесты:** Полный end-to-end flow через API Gateway

### 4.6. Безопасность — правильные решения на архитектурном уровне

- HashiCorp Vault для хранения банковских токенов
- bcrypt для хеширования паролей
- Append-only audit log в compliance-service
- 2FA (TOTP) в auth-service

### 4.7. Документация

Обширная документация:
- PRD (Product Requirements Document)
- DPIA (Data Protection Impact Assessment)
- Security Overview
- Developer Guide
- Architectural Audit

### 4.8. Интернационализация

Фронтенд имеет i18n-инфраструктуру с контекстом React, кастомным хуком `useTranslation`, и Localization-сервисом на бэкенде.

---

## 5. РЕКОМЕНДАЦИИ ПО ПРИОРИТИЗАЦИИ

### Немедленно (P0):
1. **Исправить дублирование кода** во всех файлах фронтенда и документации
2. **Реализовать реальную JWT-авторизацию** во всех сервисах (заменить `fake_auth_check`)
3. **Перевести auth-service** на PostgreSQL (убрать in-memory хранилище)
4. **Добавить Dockerfile для nginx**

### Краткосрочно (P1):
5. Зафиксировать версии зависимостей в `requirements.txt`
6. Активировать запуск тестов в CI
7. Исправить эндпоинт регистрации (JSON body вместо form data)
8. Добавить `.env.example` для секретов

### Среднесрочно (P2):
9. Добавить retry/circuit breaker для межсервисных вызовов
10. Расширить OpenTelemetry на все сервисы
11. Реализовать реальную ML-модель для категоризации
12. Заполнить Terraform/K8s конфигурации

---

## 6. ЗАКЛЮЧЕНИЕ

Проект демонстрирует **отличное архитектурное видение** и **широкий охват** технологий. Docker Compose конфигурация, выбор технологий (Vault, Weaviate, Celery, Jaeger) и общая структура репозитория заслуживают высокой оценки.

Однако **качество имплементации не соответствует заявленному уровню** "готового к промышленной эксплуатации прототипа". Критическое дублирование кода в фронтенде делает приложение неработоспособным, а повсеместное использование `fake_auth_check` делает систему полностью открытой.

Проект подходит как **демонстрация архитектурных концепций** или **учебный пример**, но требует значительной доработки для приближения к production-ready состоянию.
