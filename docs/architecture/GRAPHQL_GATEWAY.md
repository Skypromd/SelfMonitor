# GraphQL Federation Gateway (`graphql-gateway`)

## Текущее состояние

Сервис `services/graphql-gateway` настроен на **Apollo Federation** и при старте выполняет **introspection** всех перечисленных субграфов по URL вида `http://<service>:80/graphql`.

В репозитории **большинство микросервисов отдают REST (FastAPI), а не GraphQL**. Запрос к несуществующему `/graphql` приводит к **ошибке композиции схемы** и падению или нестабильной работе gateway.

Поэтому в **корневом `docker-compose.yml`** сервис `graphql-gateway` включён в **profile `graphql`** и **не** стартует при обычном `docker compose up`. Основной вход API — **nginx на порту 8000** (REST `/api/...`), он **не** зависит от graphql-gateway.

## Как запускать

```bash
docker compose --profile graphql up -d graphql-gateway
```

Доступ: `http://localhost:4000/graphql` (и `/health` на том же процессе).

## Что сделать для «боевого» Federation

1. Реализовать GraphQL-слой в сервисах (или отдельные subgraph-сервисы) с корректной федерацией.
2. Либо заменить `IntrospectAndCompose` на **статический supergraph SDL** (Rover / `supergraph.graphql`), если схема собирается отдельно.
3. Обновить переменные окружения gateway так, чтобы **каждый** URL отвечал реальным GraphQL.

## Связь с матрицей сервисов

См. `docs/architecture/SERVICES_MATRIX.md`: GraphQL gateway помечен как отдельный порт `:4000`, не проксируется через nginx `:8000`.
