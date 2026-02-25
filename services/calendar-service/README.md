# Calendar Service

Manages calendar events and reminders for users.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /events | Yes | Create a new calendar event |
| GET | /events | Yes | List calendar events with optional date range filtering |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| CALENDAR_DB_PATH | No | /tmp/calendar.db | Path to the SQLite calendar database |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
