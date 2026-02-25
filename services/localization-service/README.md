# Localization Service

Provides translation strings for different locales.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /translations/{locale}/all | No | Get all translations for a locale |
| GET | /translations/{locale}/{component} | No (deprecated) | Get translations for a specific component |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| LOCALIZATION_CATALOG_PATH | No | app/translations.json | Path to the translations JSON catalog |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
