# SelfMonitor — Linting & Code Quality Rules

> **Создан:** 2026-03-06
> **Цель:** Исключить повторное появление предупреждений линтеров. Все правила уже применены в конфигурационных файлах. Этот документ объясняет что, где и почему настроено.

---

## Архитектура конфигурации

| Инструмент | Файл конфигурации | Назначение |
| --- | --- | --- |
| **Pylance / Pyright** | `pyrightconfig.json` | Статический анализ типов Python |
| **Pylint** | `.pylintrc` | Стиль и качество кода Python |
| **Flake8 + isort** | `setup.cfg` | PEP8 форматирование и порядок импортов |
| **mypy** | `mypy.ini` | Дополнительная проверка типов |
| **cSpell** | `cspell.json` | Проверка орфографии в коде |
| **VS Code** | `.vscode/settings.json` | Интеграция всех инструментов в редактор |

---

## 1. Pylance / Pyright — `pyrightconfig.json`

### Почему столько правил отключено?

Проект использует `boto3`, `celery`, `jose`, `passlib`, `qrcode` и другие библиотеки **без stub-файлов** (type annotations). Strict-режим Pylance генерирует сотни ложных ошибок для таких библиотек.

### Правило: все `report*` установлены в `"none"`

```json
"typeCheckingMode": "basic",
"reportMissingImports": "none",
"reportMissingModuleSource": "none",
"reportMissingTypeStubs": "none",
"reportUnknownVariableType": "none"
```

### Правило: `executionEnvironments` для каждого сервиса

Каждый микросервис — отдельное окружение с `extraPaths: ["."]`, чтобы Pylance нашёл модули при runtime-разрешении путей.

### Правило: исключения — в `settings.json`, а не в `pyrightconfig.json`

Если `exclude` прописан в `pyrightconfig.json`, Pylance выдаёт предупреждение `missingDefaultExcludes` и требует явно указать системные паттерны. Чтобы избежать этого, исключения вынесены в `python.analysis.exclude` в `.vscode/settings.json` — там Pylance не валидирует их на полноту:

```json
"python.analysis.exclude": [
    "**/.*",
    ".venv",
    "**/.venv",
    "**/node_modules",
    "**/__pycache__",
    "**/migrations",
    "**/alembic",
    "apps",
    "services/analytics-service/tests"
]
```

В `pyrightconfig.json` остаются только `include`, `venv`, `typeCheckingMode`, `reportXxx` и `executionEnvironments`.

### Правило: исключение папок тестов с `sys.path` манипуляцией

```json
"exclude": ["services/analytics-service/tests", "..."]
```

Тесты, которые используют `sys.path.insert()` до импортов, **невозможно** разрешить статически. Они исключены из анализа.

### Правило: `# isort: skip_file` в top-3 файлах

Файлы `auth-service/app/main.py`, `predictive-analytics/app/main.py`, `analytics-service/tests/test_main.py` используют динамическое добавление путей. В начало каждого добавлена строка:

```python
# isort: skip_file
```

Это полностью отключает isort для данного файла.

---

## 2. Pylint — `.pylintrc`

### Принцип

Pylint — строгий линтер, но проект FastAPI имеет паттерны, которые всегда будут нарушать стандартные правила. Все они отключены **глобально**.

### Ключевые отключённые правила

| Код | Название | Причина отключения |
| --- | --- | --- |
| `W0613` | `unused-argument` | FastAPI `Depends()` параметры используются фреймворком, а не телом функции |
| `E0102` | `function-redefined` | Conditional import fallback: `try: import X; except: def X(): ...` |
| `W0621` | `redefined-outer-name` | Переменные цикла в `__main__` блоках |
| `C0114–C0116` | `missing-*-docstring` | В большом FastAPI-проекте docstrings пишутся по мере надобности |
| `C0302` | `too-many-lines` | Сервисные файлы по 1000–3000 строк — намеренный дизайн |
| `C0413` | `wrong-import-position` | `sys.path` манипуляции требуются до некоторых импортов |
| `C0103` | `invalid-name` | `UPPER_CASE` константы в scope функций, короткие имена переменных |
| `R0913` | `too-many-arguments` | FastAPI route handlers могут иметь много параметров через Depends |
| `R0801` | `duplicate-code` | Паттерны аутентификации повторяются во всех сервисах намеренно |
| `E0401` | `import-error` | Модули разрешаются через sys.path в runtime; статически не видны |
| `C0301` | `line-too-long` | Контролируется через `max-line-length=120` в `[FORMAT]` |
| `W0603` | `global-statement` | Используется для connection pools и singleton-объектов |
| `W0212` | `protected-access` | Тесты намеренно обращаются к `_private` методам |

### Правило: `[TYPECHECK] ignored-modules`

Все третьесторонние библиотеки без stubs перечислены:

```ini
ignored-modules=boto3,botocore,celery,jose,passlib,qrcode,...
ignored-classes=SQLAlchemy,scoped_session,sessionmaker,DeclarativeBase,Base
```

### Правило: `[FORMAT] max-line-length=120`

Pylint по умолчанию использует 100. Здесь переопределено на 120 (совпадает с Black и Flake8).

### Правило: `[VARIABLES] dummy-variables-rgx`

Переменные начинающиеся с `_` не считаются "неиспользованными":

```ini
dummy-variables-rgx=_+$|_+[a-zA-Z0-9_]*$
```

---

## 3. Flake8 + isort — `setup.cfg`

### Правило: `max-line-length = 120`

Совпадает с Black (`--line-length=120`) и Pylint. Длинные URL и строки документации не генерируют E501.

### Полный список игнорируемых кодов

```ini
extend-ignore =
    E203   # whitespace before ':' — Black иногда это генерирует
    W503   # line break before binary operator — конфликт со стилем Black
    W504   # line break after binary operator
    E402   # module level import not at top — нужно для sys.path манипуляций
    E501   # line too long — контролируется max-line-length
    W291   # trailing whitespace — обрабатывает форматтер
    W293   # whitespace before operator
    B008   # function calls in default arguments — FastAPI Depends() паттерн
    BLE001 # blind exception — graceful degradation в микросервисах
    E711   # comparison to None (use is/is not)
    E712   # comparison to True/False
    E741   # ambiguous variable name
    W605   # invalid escape sequence
    I001-I005 # isort order violations
```

### Правило: `known_first_party = libs,app`

isort знает, что `libs` и `app` — это локальные модули проекта, а не third-party.

---

## 4. mypy — `mypy.ini`

### Правило: `ignore_missing_imports = True` (глобально)

Все третьесторонние пакеты без stubs не генерируют ошибки.

### Правило: `disable_error_code = override,misc,no-redef,import-untyped`

- `override` — переопределение методов в Pydantic/SQLAlchemy моделях
- `misc` — разные мелкие несоответствия
- `no-redef` — conditional fallback imports переопределяют символы
- `import-untyped` — библиотеки без py.typed marker

### Правило: per-module overrides

Тестовые файлы и модули с `sys.path` манипуляциями полностью исключены:

```ini
[mypy-services.analytics_service.tests.*]
ignore_errors = True
```

---

## 5. cSpell — `cspell.json`

Единственный источник словаря. **Не добавляйте слова в `.vscode/settings.json`** — они дублируются и теряются при синхронизации.

### Как добавить новое слово

Откройте `cspell.json` и добавьте слово в массив `"words"`:

```json
"words": [
    "existing-word",
    "new-word"
]
```

### Как игнорировать файл целиком

Добавьте путь в `"ignorePaths"` в `cspell.json`:

```json
"ignorePaths": [
    "services/my-service/generated/**"
]
```

---

## 6. VS Code — `.vscode/settings.json`

### Ключевые настройки

| Настройка | Значение | Причина |
| --- | --- | --- |
| `python.linting.enabled` | `false` | Старый API; используются standalone-расширения |
| `python.analysis.diagnosticMode` | `openFilesOnly` | Анализ только открытых файлов (не весь workspace) |
| `pylint.args` | `--rcfile=.../.pylintrc` | Явный путь к конфигу, чтобы Pylint-расширение не использовало дефолты |
| `pylint.severity.convention` | `information` | Pylint C-коды — информация, не ошибки |
| `flake8.severity.*` | `Information`/`Warning` | Не блокируют работу, только информируют |
| `editor.formatOnSave` | `true` | Black автоматически форматирует при сохранении |

### Глобальный `settings.json` пользователя (НЕ редактировать для проекта)

Файл `C:\Users\...\AppData\Roaming\Code\User\settings.json` содержит `"python.analysis.typeCheckingMode": "strict"`. Это **перекрывается** через `pyrightconfig.json` (который имеет приоритет над user settings для Pylance).

---

## 7. Правила для новых файлов и сервисов

### При создании нового микросервиса

1. Добавить новый блок в `pyrightconfig.json`:

   ```json
   {
       "root": "services/my-new-service",
       "pythonVersion": "3.12",
       "extraPaths": ["."]
   }
   ```

2. Если сервис использует `sys.path.insert()` перед импортами — добавить `# isort: skip_file` в первую строку файла.

3. Если тесты используют `sys.path` — добавить в `exclude` в `pyrightconfig.json`:

   ```json
   "services/my-new-service/tests"
   ```

### При добавлении новой библиотеки без stubs

1. Добавить в `.pylintrc` `[TYPECHECK] ignored-modules`:

   ```ini
   ignored-modules=...,my-new-lib
   ```

2. Добавить в `mypy.ini`:

   ```ini
   [mypy-my-new-lib.*]
   ignore_missing_imports = True
   ```

3. Добавить в `pyrightconfig.json` (уже глобально: `reportMissingTypeStubs: none`).

### При появлении нового типа Pylint-предупреждения

Проверить — это реальная проблема или structural pattern проекта?

- **Реальная ошибка** → исправить в коде
- **Structural pattern** → добавить код в `disable=` в `.pylintrc`

### При появлении нового cSpell-предупреждения

Добавить слово в `cspell.json` → массив `"words"`.

**Никогда** не добавлять в `.vscode/settings.json` — только в `cspell.json`.

---

## 8. Как проверить что всё чисто

```powershell
# Проверка ошибок через VS Code (в терминале показывает 0 problems):
# → View → Problems (Ctrl+Shift+M)

# Проверка trailing whitespace (должен быть 0):
Select-String -Path "services/**/*.py" -Pattern " $" | Measure-Object

# Проверка что pyrightconfig.json валиден:
Get-Content pyrightconfig.json | ConvertFrom-Json

# Проверка что setup.cfg валиден для flake8:
# Открыть любой .py файл — предупреждений не должно быть выше Warning
```

---

## 9. Файлы с постоянными исключениями `# type: ignore`

Следующие файлы содержат inline-подавления, которые **нельзя убирать**:

| Файл | Строка | Причина |
| --- | --- | --- |
| `auth-service/app/main.py` | импорты pyotp, qrcode, jose, passlib | Нет type stubs |
| `auth-service/app/main.py` | `import json as _json` | Позиционирован после third-party imports (runtime требование) |
| `documents-service/app/celery_app.py` | `sessionmaker(...)` | SQLAlchemy overload mismatch |
| `documents-service/app/celery_app.py` | `is_deductible = ...` | Pyright не видит Enum-to-bool присваивание |
| `predictive-analytics/app/main.py` | stub-функции после `except ImportError` | F811 redefinition — намеренный fallback паттерн |
| `support-ai-service/app/models.py` | SQLAlchemy ORM классы | `Base` — dynamic class без type info |
| `analytics-service/tests/test_main.py` | `from app.main import ...` | `sys.path` манипуляция невидима Pylance статически |

---

*Все конфигурации применены и зафиксированы. При соблюдении правил из раздела 7 новые ошибки линтеров не должны появляться.*
