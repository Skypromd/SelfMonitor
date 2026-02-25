import logging
from celery import Celery
import os
import time
import random
import datetime
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio

from . import crud, schemas

# --- DB & Service URL Setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/db_documents")
QNA_SERVICE_URL = os.getenv("QNA_SERVICE_URL", "http://localhost:8014/index")
QNA_INTERNAL_TOKEN = os.getenv("QNA_INTERNAL_TOKEN")
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# --- Celery Setup ---
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

logger = logging.getLogger(__name__)

celery = Celery(__name__, broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

def index_document_content(user_id: str, doc_id: str, filename: str, content: str):
    """Synchronous function to call the Q&A service for indexing."""
    if not QNA_INTERNAL_TOKEN:
        logger.error("Error indexing document: QNA_INTERNAL_TOKEN is not configured.")
        return

    try:
        with httpx.Client() as client:
            response = client.post(
                QNA_SERVICE_URL,
                headers={"X-Internal-Token": QNA_INTERNAL_TOKEN},
                json={
                    "user_id": user_id,
                    "document_id": doc_id,
                    "filename": filename,
                    "text_content": content,
                },
                timeout=10.0
            )
            response.raise_for_status()
        logger.info("Successfully indexed document %s in Q&A service.", doc_id)
    except httpx.RequestError as e:
        logger.error("Error indexing document %s: %s", doc_id, e)

@celery.task
def ocr_processing_task(document_id: str, user_id: str, filename: str):
    """
    Simulates OCR and then calls the Q&A service to index the content.
    """
    logger.info("Starting OCR processing for document: %s", document_id)
    time.sleep(5) # Simulate long-running task

    # 1. Simulate OCR result
    extracted_data = schemas.ExtractedData(
        total_amount=round(random.uniform(5.0, 200.0), 2),
        vendor_name=random.choice(["Tesco", "Amazon", "Costa Coffee", "Trainline"]),
        transaction_date=datetime.date.today() - datetime.timedelta(days=random.randint(1, 30))
    )

    # 2. Update our main DB with the results
    async def update_db():
        async with AsyncSessionLocal() as session:
            await crud.update_document_with_ocr_results(
                db=session,
                doc_id=document_id,
                status="completed",
                extracted_data=extracted_data
            )
    asyncio.run(update_db())
    logger.info("Finished OCR processing for document: %s", document_id)

    # 3. Create a simple text representation and index it
    text_content = f"Receipt from {extracted_data.vendor_name} for the amount of {extracted_data.total_amount} on {extracted_data.transaction_date}."
    index_document_content(user_id, document_id, filename, text_content)

    return {"document_id": document_id, "status": "completed", "vendor": extracted_data.vendor_name}
