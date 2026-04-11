# Smoke-тесты через gateway в CI

Локально после `docker compose up -d` (с **nginx-gateway** на `:8000`):

```bash
GATEWAY_URL=http://localhost:8000 ./scripts/smoke_gateway_health.sh
```

## Пример шага GitHub Actions

Полный прогон зависит от вашего compose (сколько сервисов поднимать). Минимальный паттерн:

```yaml
  gateway-smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start stack
        run: docker compose up -d nginx-gateway auth-service transactions-service
      - name: Wait for gateway
        run: |
          for i in $(seq 1 60); do
            curl -sSf http://localhost:8000/health && break
            sleep 2
          done
      - name: Smoke API health via gateway
        env:
          GATEWAY_URL: http://localhost:8000
        run: bash scripts/smoke_gateway_health.sh
```

Подставьте список сервисов из вашего `docker-compose.yml`, чтобы все пути из скрипта отвечали **200**. При необходимости сократите `paths` в `scripts/smoke_gateway_health.sh` под «лёгкий» профиль CI.
