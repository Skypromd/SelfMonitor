# Documents Service

Handles document uploads, orchestrates OCR processing, and stores extracted data.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /documents/upload | Yes | Upload a document to S3 and trigger OCR processing |
| GET | /documents | Yes | List all documents for the authenticated user |
| GET | /documents/{document_id} | Yes | Retrieve metadata for a specific document |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| DATABASE_URL | No | postgresql+asyncpg://user:password@localhost/db_documents | PostgreSQL connection string |
| S3_BUCKET_NAME | No | documents-bucket | S3 bucket name for document storage |
| AWS_ENDPOINT_URL | No | - | S3-compatible endpoint URL (e.g. LocalStack) |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
