# Business Intelligence Service

Advanced analytics and data monetization platform for comprehensive business insights.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /revenue-intelligence | Yes | Comprehensive revenue intelligence and optimization insights |
| GET | /customer-intelligence | Yes | Advanced customer behavior analytics and segmentation |
| GET | /market-intelligence | Yes | Market trends and competitive intelligence analytics |
| GET | /data-monetization-analytics | Yes | Data monetization strategies and revenue opportunities |
| POST | /generate-business-insights | Yes | AI-powered business insights generation |
| GET | /executive-dashboard | Yes | Executive-level KPIs and strategic insights |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
