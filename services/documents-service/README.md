# Documents Service

Handles document uploads, orchestrates OCR processing, and stores extracted data.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /documents/upload | Yes | Upload a document to S3 and trigger OCR processing |
| GET | /documents | Yes | List all documents for the authenticated user |
| GET | /documents/{document_id} | Yes | Retrieve metadata for a specific document |
| PATCH | /documents/{document_id}/review | Yes | Update OCR review fields; when `COMPLIANCE_SERVICE_URL` is set, emits audit `document_review_updated` |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| COMPLIANCE_SERVICE_URL | No | - | Base URL of compliance-service; when set, successful upload emits `document_uploaded`, successful review PATCH emits `document_review_updated` |
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
