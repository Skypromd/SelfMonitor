import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

# --- Configuration ---
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
EMBEDDING_MODEL_NAME = os.getenv("QNA_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_weaviate_client: Any | None = None
_embedding_model: Any | None = None

_, get_current_user_id = build_jwt_auth_dependencies()


def _get_weaviate_client() -> Any | None:
    global _weaviate_client
    if _weaviate_client is not None:
        return _weaviate_client
    try:
        import weaviate

        _weaviate_client = weaviate.Client(WEAVIATE_URL)
        print("Successfully connected to Weaviate.")
    except Exception as exc:  # noqa: BLE001 - surface unavailability as runtime 503
        print(f"Error connecting to Weaviate: {exc}")
        _weaviate_client = None
    return _weaviate_client


def _get_embedding_model() -> Any:
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Embedding model not available") from exc
    _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _require_weaviate_client() -> Any:
    client = _get_weaviate_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Weaviate not available")
    return client


def ensure_schema_exists() -> None:
    client = _get_weaviate_client()
    if client and not client.schema.exists("DocumentChunk"):
        logger.info("Creating 'DocumentChunk' schema in Weaviate...")
        document_schema = {
            "class": "DocumentChunk",
            "description": "A chunk of text from a user's document",
            "properties": [
                {"name": "user_id", "dataType": ["text"]},
                {"name": "document_id", "dataType": ["text"]},
                {"name": "filename", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]},
            ],
        }
        client.schema.create_class(document_schema)
        logger.info("Schema created.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_schema_exists()
    yield


app = FastAPI(
    title="Q&A and Semantic Search Service",
    description="Handles creating text embeddings and searching for documents.",
    version="1.0.0",
    lifespan=lifespan,
)


# --- API Models ---
class IndexRequest(BaseModel):
    document_id: str
    filename: str
    text_content: str


class SearchRequest(BaseModel):
    query: str


class SearchResult(BaseModel):
    document_id: str
    filename: str
    content: str
    score: float


# --- Endpoints ---
@app.post("/index")
async def index_document(
    request: IndexRequest,
    user_id: str = Depends(get_current_user_id),
):
    client = _require_weaviate_client()
    vector = _get_embedding_model().encode(request.text_content).tolist()
    data_object = {
        "user_id": user_id,
        "document_id": request.document_id,
        "filename": request.filename,
        "content": request.text_content,
    }
    client.data_object.create(
        data_object=data_object,
        class_name="DocumentChunk",
        vector=vector,
    )
    return {"message": "Document indexed successfully."}


@app.post("/search", response_model=list[SearchResult])
async def search_documents(
    request: SearchRequest,
    user_id: str = Depends(get_current_user_id),
):
    client = _require_weaviate_client()
    query_vector = _get_embedding_model().encode(request.query).tolist()
    result = (
        client.query.get("DocumentChunk", ["document_id", "filename", "content"])
        .with_near_vector({"vector": query_vector})
        .with_where({
            "path": ["user_id"],
            "operator": "Equal",
            "valueText": user_id,
        })
        .with_limit(5)
        .with_additional(["distance"])
        .do()
    )

    hits = result.get("data", {}).get("Get", {}).get("DocumentChunk", [])
    return [
        SearchResult(
            document_id=str(hit.get("document_id", "")),
            filename=str(hit.get("filename", "")),
            content=str(hit.get("content", "")),
            score=float(hit.get("_additional", {}).get("distance", 0.0)),
        )
        for hit in hits
    ]
