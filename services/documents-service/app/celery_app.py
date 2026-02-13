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
from .expense_classifier import suggest_category_from_keywords, to_expense_article

# --- DB & Service URL Setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/db_documents")
QNA_SERVICE_URL = os.getenv("QNA_SERVICE_URL", "http://localhost:8014/index")
CATEGORIZATION_SERVICE_URL = os.getenv("CATEGORIZATION_SERVICE_URL", "http://categorization-service/categorize")
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# --- Celery Setup ---
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery = Celery(__name__, broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


def suggest_expense_category(description: str) -> str | None:
    """Try categorization-service first, then fallback to local keyword rules."""
    normalized_description = description.strip()
    if not normalized_description:
        return None

    try:
        with httpx.Client() as client:
            response = client.post(
                CATEGORIZATION_SERVICE_URL,
                json={"description": normalized_description},
                timeout=4.0,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                category = payload.get("category")
                if isinstance(category, str) and category.strip():
                    return category.strip()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        print(f"Warning: categorization-service unavailable for receipt scan: {exc}")

    return suggest_category_from_keywords(normalized_description)

def index_document_content(user_id: str, doc_id: str, filename: str, content: str):
    """Synchronous function to call the Q&A service for indexing."""
    try:
        with httpx.Client() as client:
            response = client.post(
                QNA_SERVICE_URL,
                json={
                    "user_id": user_id,
                    "document_id": doc_id,
                    "filename": filename,
                    "text_content": content,
                },
                timeout=10.0
            )
            response.raise_for_status()
        print(f"Successfully indexed document {doc_id} in Q&A service.")
    except httpx.RequestError as e:
        print(f"Error indexing document {doc_id}: {e}")

@celery.task
def ocr_processing_task(document_id: str, user_id: str, filename: str):
    """
    Simulates OCR and then calls the Q&A service to index the content.
    """
    print(f"Starting OCR processing for document: {document_id}")
    time.sleep(5) # Simulate long-running task

    # 1. Simulate OCR result
    extracted_data = schemas.ExtractedData(
        total_amount=round(random.uniform(5.0, 200.0), 2),
        vendor_name=random.choice(
            [
                "Tesco Business",
                "Amazon Business",
                "Costa Coffee",
                "Trainline",
                "Notion Labs",
                "Uber",
            ]
        ),
        transaction_date=datetime.date.today() - datetime.timedelta(days=random.randint(1, 30))
    )
    category_hint = suggest_expense_category(f"{extracted_data.vendor_name} {filename}")
    expense_article, is_deductible = to_expense_article(category_hint)
    extracted_data.suggested_category = category_hint
    extracted_data.expense_article = expense_article
    extracted_data.is_potentially_deductible = is_deductible

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
    print(f"Finished OCR processing for document: {document_id}")

    # 3. Create a simple text representation and index it
    text_content = (
        f"Receipt from {extracted_data.vendor_name} for the amount of {extracted_data.total_amount} "
        f"on {extracted_data.transaction_date}. Suggested category: {extracted_data.suggested_category}. "
        f"Expense article: {extracted_data.expense_article}. "
        f"Potentially deductible: {extracted_data.is_potentially_deductible}."
    )
    index_document_content(user_id, document_id, filename, text_content)

    return {
        "document_id": document_id,
        "status": "completed",
        "vendor": extracted_data.vendor_name,
        "suggested_category": extracted_data.suggested_category,
        "expense_article": extracted_data.expense_article,
    }
