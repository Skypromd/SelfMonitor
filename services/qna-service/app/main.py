import logging
import os
from typing import Annotated

import weaviate
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# --- Configuration ---
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
QNA_INTERNAL_TOKEN = os.getenv("QNA_INTERNAL_TOKEN")
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
# Load a small but effective model for generating sentence embeddings
logger = logging.getLogger(__name__)

model = SentenceTransformer('all-MiniLM-L6-v2')

app = FastAPI(
    title="Q&A and Semantic Search Service",
    description="Handles creating text embeddings and searching for documents.",
    version="1.0.0"
)

# --- Weaviate Client and Schema ---
try:
    client_kwargs = {}
    if WEAVIATE_API_KEY:
        client_kwargs["auth_client_secret"] = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
    client = weaviate.Client(WEAVIATE_URL, **client_kwargs)
    logger.info("Successfully connected to Weaviate.")
except Exception as e:
    logger.error("Error connecting to Weaviate: %s", e)
    client = None

def ensure_schema_exists():
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
            ]
        }
        client.schema.create_class(document_schema)
        logger.info("Schema created.")

@app.on_event("startup")
def startup_event():
    ensure_schema_exists()


@app.get("/health")
async def health_check():
    if not client:
        raise HTTPException(status_code=503, detail="Weaviate not available")
    return {"status": "ok"}


def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    return user_id

# --- API Models ---
class IndexRequest(BaseModel):
    user_id: str
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
    internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
):
    if not client:
        raise HTTPException(status_code=503, detail="Weaviate not available")
    if not QNA_INTERNAL_TOKEN:
        raise HTTPException(status_code=503, detail="QnA internal token is not configured")
    if internal_token != QNA_INTERNAL_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized internal caller")

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
async def search_documents(
    request: SearchRequest,
    user_id: str = Depends(get_current_user_id),
):
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
            "valueText": user_id,
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
