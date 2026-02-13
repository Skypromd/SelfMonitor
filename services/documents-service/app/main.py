import os
import sys
import uuid
from pathlib import Path
from typing import List
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from . import crud, models, schemas
from .database import get_db
from .celery_app import ocr_processing_task

# --- S3 Configuration ---
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "documents-bucket")
# For local development with LocalStack, boto3 needs the endpoint_url.
S3_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")

# Configure boto3 client
s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    config=Config(signature_version='s3v4')
)

app = FastAPI(
    title="Documents Service",
    description="Handles document uploads, orchestrates OCR processing, and stores extracted data.",
    version="1.0.0"
)

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

@app.post("/documents/upload", response_model=schemas.Document, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...), 
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Accepts a document, uploads it to S3, creates a DB record, and triggers OCR."""
    file_extension = os.path.splitext(file.filename)[1]
    s3_key = f"{user_id}/{uuid.uuid4()}{file_extension}"

    try:
        s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, s3_key)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file to S3: {e}")

    db_document = await crud.create_document(db, user_id=user_id, filename=file.filename, filepath=s3_key)

    # Trigger background OCR task with persisted file key.
    ocr_processing_task.delay(
        str(db_document.id),
        db_document.user_id,
        db_document.filename,
        db_document.filepath,
    )

    return db_document

@app.get("/documents", response_model=List[schemas.Document])
async def list_documents(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Lists all documents for the authenticated user from the database."""
    return await crud.get_documents_by_user(db, user_id=user_id)


@app.get("/documents/{document_id}", response_model=schemas.Document)
async def get_document(
    document_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves metadata for a specific document."""
    db_document = await crud.get_document_by_id(db, user_id=user_id, doc_id=document_id)
    if db_document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return db_document
