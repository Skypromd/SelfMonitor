# Cost Optimization Service

Automated infrastructure scaling, cost monitoring, and efficiency optimization.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /cost-analysis | Yes | Analyze current monthly costs and identify optimizations |
| POST | /implement-optimization/{optimization_type} | Yes | Implement a specific cost optimization strategy |
| GET | /cost-efficiency-metrics | Yes | Get cost efficiency and optimization metrics |
| GET | /automation-recommendations | Yes | Get AI-powered automation recommendations |
| POST | /deploy-full-optimization | Yes | Deploy comprehensive cost optimization across all areas |
| GET | /optimization-dashboard | Yes | Real-time cost optimization dashboard |

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
