# Q&A and Semantic Search Service

Handles creating text embeddings and searching for documents.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check (returns 503 if Weaviate is unavailable) |
| POST | /index | Internal (X-Internal-Token) | Index a document chunk with its embedding |
| POST | /search | Yes | Semantic search across user's documents |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| WEAVIATE_URL | No | http://localhost:8080 | Weaviate vector database URL |
| WEAVIATE_API_KEY | No | - | Weaviate API key for authentication |
| QNA_INTERNAL_TOKEN | No | - | Internal token for service-to-service indexing calls |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
