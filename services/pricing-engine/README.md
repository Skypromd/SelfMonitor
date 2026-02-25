# Smart Pricing Engine

Dynamic pricing, usage tracking, and optimization for maximum revenue and retention.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /pricing-plans | No | Get all available pricing plans |
| GET | /usage/{user_id} | Yes | Get current usage statistics for a user |
| POST | /track-usage | Yes | Track a usage event for billing and limits |
| GET | /pricing-recommendation/{user_id} | Yes | AI-powered pricing recommendation based on usage |
| GET | /dynamic-pricing/{user_id} | Yes | Get personalized pricing with smart discounts |
| GET | /pricing-analytics | Yes | Analytics dashboard for pricing optimization |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| REDIS_URL | No | redis://localhost:6379 | Redis URL for real-time usage tracking |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
