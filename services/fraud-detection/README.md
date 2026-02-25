# Fraud Detection Service

Real-time fraud detection and risk monitoring for enhanced security monetization.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| GET | /fraud-risk-assessment/{user_id} | Yes | Real-time fraud risk assessment for a user |
| POST | /fraud-alerts | Yes | Create and process a fraud alert with automated response |
| GET | /fraud-analytics | Yes | Comprehensive fraud analytics and prevention metrics |
| GET | /compliance-monitoring | Yes | Real-time compliance monitoring and AML/KYC automation |
| POST | /automated-compliance-check | Yes | Automated compliance checking for transactions |
| GET | /security-monetization-metrics | Yes | Security and compliance monetization impact metrics |

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
