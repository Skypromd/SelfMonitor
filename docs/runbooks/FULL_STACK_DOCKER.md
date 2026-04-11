# Полный запуск бэкенда (все сервисы из `docker-compose.yml`)

## Одна команда (рекомендуется)

Включает **все** контейнеры из корневого compose, **включая GraphQL Federation** (`graphql-gateway` иначе не стартует — у него profile `graphql`):

```bash
cp .env.example .env
# Отредактируйте .env (см. AGENTS.md: postgres-master, пароли, опционально S3_ACCESS_KEY / S3_SECRET_KEY)

docker compose --profile graphql up --build -d
```

Проверка:

```bash
docker compose --profile graphql ps
```

API gateway (REST): **http://localhost:8000**  
GraphQL (если поднят профиль): **http://localhost:4000/graphql**

## Без GraphQL

Если Federation не нужен (основной вход — nginx REST):

```bash
docker compose up --build -d
```

## Фронтенды (не в Docker Compose)

| Модуль | Команда | URL |
|--------|---------|-----|
| Web | `cd apps/web-portal && npm install && npm run dev` | http://localhost:3000 |
| Mobile | `cd apps/mobile && npm install && npx expo start` | Expo |

## Чего **нет** в корневом `docker-compose.yml`

Сервисы из репозитория, которые **не** стартуют с этой командой (см. `docs/architecture/SERVICES_MATRIX.md`): например отдельные заготовки **ai-agent-service** как subgraph, **business-intelligence**, **fraud-detection** и т.д. — их нет в compose, пока не добавят в файл.

Альтернативный стек **multi-tenant** — файл `docker-compose-multitenant.yml` (другая топология), не смешивайте с основным без понимания цели.

## Частые проблемы

- **Alembic на старте** до готовности Postgres → `docker compose restart <service>` после healthy БД (`AGENTS.md`).
- **502 у nginx** после перезапуска upstream → `docker compose restart nginx-gateway`.
- Предупреждения про `S3_ACCESS_KEY` / `BACKUP_WEBHOOK_URL` — задайте в `.env` или оставьте пустыми для локали.

---

Скрипт из корня репозитория: `scripts/run_full_stack.ps1` (Windows).
