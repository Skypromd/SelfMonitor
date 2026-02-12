import os
from contextlib import asynccontextmanager

import weaviate
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# --- Configuration ---
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
# Load a small but effective model for generating sentence embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

# --- Weaviate Client and Schema ---
try:
    client = weaviate.Client(WEAVIATE_URL)
    print("Successfully connected to Weaviate.")
except Exception as e:
    print(f"Error connecting to Weaviate: {e}")
    client = None

def ensure_schema_exists():
    if client and not client.schema.exists("DocumentChunk"):
        print("Creating 'DocumentChunk' schema in Weaviate...")
        document_schema = {
            "class": "DocumentChunk",
            "description": "A chunk of text from a user's document",
            "properties": [
                {"name": "user_id", "dataType": ["text"]},
                {"name": "document_id", "dataType": ["text"]},
                {"name": "filename", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]},
            ]
        }
        client.schema.create_class(document_schema)
        print("Schema created.")


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
    user_id: str
    document_id: str
    filename: str
    text_content: str

class SearchRequest(BaseModel):
    user_id: str
    query: str

class SearchResult(BaseModel):
    document_id: str
    filename: str
    content: str
    score: float

# --- Endpoints ---
@app.post("/index")
async def index_document(request: IndexRequest):
    if not client:
        raise HTTPException(status_code=503, detail="Weaviate not available")

    # 1. Generate embedding for the text content
    vector = model.encode(request.text_content).tolist()

    # 2. Create data object to store in Weaviate
    data_object = {
        "user_id": request.user_id,
        "document_id": request.document_id,
        "filename": request.filename,
        "content": request.text_content,
    }

    # 3. Add the object with its vector to Weaviate
    client.data_object.create(
        data_object=data_object,
        class_name="DocumentChunk",
        vector=vector
    )
    return {"message": "Document indexed successfully."}

@app.post("/search", response_model=list[SearchResult])
async def search_documents(request: SearchRequest):
    if not client:
        raise HTTPException(status_code=503, detail="Weaviate not available")

    # 1. Generate embedding for the user's query
    query_vector = model.encode(request.query).tolist()

    # 2. Perform the search in Weaviate
    result = (
        client.query
        .get("DocumentChunk", ["document_id", "filename", "content"])
        .with_near_vector({"vector": query_vector})
        .with_where({
            "path": ["user_id"],
            "operator": "Equal",
            "valueText": request.user_id,
        })
        .with_limit(5)
        .with_additional(["distance"]) # 'distance' is Weaviate's measure of similarity
        .do()
    )

    hits = result["data"]["Get"]["DocumentChunk"]

    # 3. Format the results
    return [
        SearchResult(
            document_id=hit["document_id"],
            filename=hit["filename"],
            content=hit["content"],
            score=hit["_additional"]["distance"]
        ) for hit in hits
    ]
