import asyncio
import datetime
import os

import boto3
import httpx
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from celery import Celery
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from . import crud, schemas
from .expense_classifier import suggest_category_from_keywords, to_expense_article
from .ocr_pipeline import (
    OCRPipelineError,
    build_text_excerpt,
    evaluate_ocr_quality,
    extract_document_text,
    extract_total_amount,
    extract_transaction_date,
    infer_vendor_name,
)

# --- DB & Service URL Setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/db_documents")
QNA_SERVICE_URL = os.getenv("QNA_SERVICE_URL", "http://localhost:8014/index")
CATEGORIZATION_SERVICE_URL = os.getenv("CATEGORIZATION_SERVICE_URL", "http://categorization-service/categorize")
TRANSACTIONS_SERVICE_URL = os.getenv(
    "TRANSACTIONS_SERVICE_URL",
    "http://transactions-service/transactions/receipt-drafts",
)
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "documents-bucket")
S3_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
OCR_REVIEW_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_REVIEW_CONFIDENCE_THRESHOLD", "0.75"))

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    config=Config(signature_version="s3v4"),
)

# --- Celery Setup ---
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

logger = logging.getLogger(__name__)

celery = Celery(__name__, broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


def _build_user_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": int(datetime.datetime.now(datetime.UTC).timestamp()),
    }
    return jwt.encode(payload, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)


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


async def _load_manual_feedback(
    *,
    user_id: str,
    vendor_name: str | None,
) -> dict[str, str | bool] | None:
    async with AsyncSessionLocal() as session:
        return await crud.get_latest_category_feedback_for_vendor(
            session,
            user_id=user_id,
            vendor_name=vendor_name,
        )


def index_document_content(user_id: str, doc_id: str, filename: str, content: str):
    """Synchronous function to call the Q&A service for indexing."""
    if not QNA_INTERNAL_TOKEN:
        logger.error("Error indexing document: QNA_INTERNAL_TOKEN is not configured.")
        return

    try:
        token = _build_user_token(user_id)
        with httpx.Client() as client:
            response = client.post(
                QNA_SERVICE_URL,
                headers={"X-Internal-Token": QNA_INTERNAL_TOKEN},
                json={
                    "document_id": doc_id,
                    "filename": filename,
                    "text_content": content,
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            response.raise_for_status()
        print(f"Successfully indexed document {doc_id} in Q&A service.")
    except httpx.RequestError as exc:
        print(f"Error indexing document {doc_id}: {exc}")


def create_receipt_draft_transaction(
    *,
    document_id: str,
    user_id: str,
    filename: str,
    extracted_data: schemas.ExtractedData,
) -> tuple[str | None, bool | None]:
    if extracted_data.total_amount is None or extracted_data.transaction_date is None:
        return None, None

    payload = {
        "document_id": document_id,
        "filename": filename,
        "transaction_date": extracted_data.transaction_date.isoformat(),
        "total_amount": float(abs(extracted_data.total_amount)),
        "currency": "GBP",
        "vendor_name": extracted_data.vendor_name,
        "suggested_category": extracted_data.suggested_category,
        "expense_article": extracted_data.expense_article,
        "is_potentially_deductible": extracted_data.is_potentially_deductible,
    }

    try:
        token = _build_user_token(user_id)
        with httpx.Client() as client:
            response = client.post(
                TRANSACTIONS_SERVICE_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            response_payload = response.json() if response.content else {}
            if not isinstance(response_payload, dict):
                return None, None
            transaction = response_payload.get("transaction")
            duplicated = response_payload.get("duplicated")
            transaction_id = transaction.get("id") if isinstance(transaction, dict) else None
            resolved_id = str(transaction_id) if transaction_id else None
            resolved_duplicate = bool(duplicated) if duplicated is not None else None
            return resolved_id, resolved_duplicate
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        print(f"Error creating receipt draft transaction for {document_id}: {exc}")
        return None, None


def _download_document_bytes(filepath: str) -> bytes:
    response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=filepath)
    body = response.get("Body")
    if body is None:
        raise OCRPipelineError("s3_missing_body")
    data = body.read()
    if not data:
        raise OCRPipelineError("s3_empty_document")
    return data


async def _build_extracted_data_from_text(
    *,
    user_id: str,
    text: str,
    provider: str,
    filename: str,
) -> schemas.ExtractedData:
    total_amount = extract_total_amount(text)
    transaction_date = extract_transaction_date(text)
    vendor_name = infer_vendor_name(text=text, filename=filename)
    description = " ".join(
        part for part in [vendor_name or "", filename, build_text_excerpt(text, limit=120) or ""] if part
    )
    manual_feedback = await _load_manual_feedback(user_id=user_id, vendor_name=vendor_name)
    if manual_feedback and isinstance(manual_feedback.get("suggested_category"), str):
        suggested_category = str(manual_feedback["suggested_category"])
        expense_article = (
            str(manual_feedback["expense_article"])
            if isinstance(manual_feedback.get("expense_article"), str)
            else None
        )
        is_deductible = (
            bool(manual_feedback["is_potentially_deductible"])
            if isinstance(manual_feedback.get("is_potentially_deductible"), bool)
            else None
        )
        if expense_article is None or is_deductible is None:
            derived_article, derived_deductible = to_expense_article(suggested_category)
            if expense_article is None:
                expense_article = derived_article
            if is_deductible is None:
                is_deductible = derived_deductible
    else:
        suggested_category = suggest_expense_category(description)
        expense_article, is_deductible = to_expense_article(suggested_category)
    quality = evaluate_ocr_quality(
        text=text,
        total_amount=total_amount,
        transaction_date=transaction_date,
        vendor_name=vendor_name,
        threshold=OCR_REVIEW_CONFIDENCE_THRESHOLD,
    )

    return schemas.ExtractedData(
        total_amount=total_amount,
        vendor_name=vendor_name,
        transaction_date=transaction_date,
        suggested_category=suggested_category,
        expense_article=expense_article,
        is_potentially_deductible=is_deductible,
        ocr_provider=provider,
        raw_text_excerpt=build_text_excerpt(text, limit=320),
        ocr_confidence=quality.confidence,
        needs_review=quality.needs_review,
        review_reason=quality.reason,
        review_status="pending" if quality.needs_review else "confirmed",
        reviewed_at=None,
        review_notes=None,
    )


def _create_index_text(extracted_data: schemas.ExtractedData, raw_text: str) -> str:
    summary_parts = [
        f"Vendor: {extracted_data.vendor_name}" if extracted_data.vendor_name else None,
        f"Amount: {extracted_data.total_amount}" if extracted_data.total_amount is not None else None,
        f"Date: {extracted_data.transaction_date}" if extracted_data.transaction_date else None,
        f"Category: {extracted_data.suggested_category}" if extracted_data.suggested_category else None,
        f"Expense article: {extracted_data.expense_article}" if extracted_data.expense_article else None,
        (
            f"Potentially deductible: {extracted_data.is_potentially_deductible}"
            if extracted_data.is_potentially_deductible is not None
            else None
        ),
        (
            f"Draft transaction ID: {extracted_data.receipt_draft_transaction_id}"
            if extracted_data.receipt_draft_transaction_id
            else None
        ),
        f"OCR confidence: {extracted_data.ocr_confidence}" if extracted_data.ocr_confidence is not None else None,
        f"Needs review: {extracted_data.needs_review}" if extracted_data.needs_review is not None else None,
        f"Review reason: {extracted_data.review_reason}" if extracted_data.review_reason else None,
    ]
    summary = ". ".join(part for part in summary_parts if part)
    if raw_text.strip():
        return f"{summary}\n\nOCR text:\n{raw_text[:5000]}" if summary else raw_text[:5000]
    return summary


async def _load_filepath_for_document(document_id: str) -> str | None:
    async with AsyncSessionLocal() as session:
        document = await crud.get_document_for_processing(session, doc_id=document_id)
        return document.filepath if document else None


async def _update_document_ocr_state(
    *,
    document_id: str,
    status: str,
    extracted_data: schemas.ExtractedData,
) -> None:
    async with AsyncSessionLocal() as session:
        await crud.update_document_with_ocr_results(
            db=session,
            doc_id=document_id,
            status=status,
            extracted_data=extracted_data,
        )


@celery.task
def ocr_processing_task(document_id: str, user_id: str, filename: str, filepath: str | None = None):
    """
    Processes uploaded document via real OCR provider and stores extracted fields.
    """
    print(f"Starting OCR processing for document: {document_id}")
    resolved_filepath = filepath or asyncio.run(_load_filepath_for_document(document_id))
    if not resolved_filepath:
        extracted_data = schemas.ExtractedData(
            ocr_provider=os.getenv("OCR_PROVIDER", "textract"),
            raw_text_excerpt=None,
            ocr_confidence=0.0,
            needs_review=True,
            review_reason="filepath_not_found",
            review_status="pending",
        )
        asyncio.run(_update_document_ocr_state(document_id=document_id, status="failed", extracted_data=extracted_data))
        print(f"OCR failed: file path not found for document {document_id}")
        return {"document_id": document_id, "status": "failed", "reason": "filepath_not_found"}

    try:
        file_bytes = _download_document_bytes(resolved_filepath)
        ocr_result = extract_document_text(file_bytes)
        if not ocr_result.text.strip():
            raise OCRPipelineError("ocr_empty_text")
        extracted_data = asyncio.run(
            _build_extracted_data_from_text(
                user_id=user_id,
                text=ocr_result.text,
                provider=ocr_result.provider,
                filename=filename,
            )
        )
        receipt_transaction_id, receipt_transaction_duplicated = create_receipt_draft_transaction(
            document_id=document_id,
            user_id=user_id,
            filename=filename,
            extracted_data=extracted_data,
        )
        extracted_data.receipt_draft_transaction_id = receipt_transaction_id
        extracted_data.receipt_draft_duplicated = receipt_transaction_duplicated
        if extracted_data.needs_review is not True:
            extracted_data.reviewed_at = datetime.datetime.now(datetime.UTC)
        asyncio.run(
            _update_document_ocr_state(
                document_id=document_id,
                status="completed",
                extracted_data=extracted_data,
            )
        )

        indexed_text = _create_index_text(extracted_data=extracted_data, raw_text=ocr_result.text)
        if indexed_text:
            index_document_content(user_id, document_id, filename, indexed_text)

        print(f"Finished OCR processing for document: {document_id}")
        return {
            "document_id": document_id,
            "status": "completed",
            "vendor": extracted_data.vendor_name,
            "suggested_category": extracted_data.suggested_category,
            "expense_article": extracted_data.expense_article,
            "ocr_provider": extracted_data.ocr_provider,
        }
    except (OCRPipelineError, ClientError, BotoCoreError) as exc:
        failed_data = schemas.ExtractedData(
            ocr_provider=os.getenv("OCR_PROVIDER", "textract"),
            raw_text_excerpt=f"OCR failed: {exc}",
            ocr_confidence=0.0,
            needs_review=True,
            review_reason="ocr_failed",
            review_status="pending",
        )
        asyncio.run(_update_document_ocr_state(document_id=document_id, status="failed", extracted_data=failed_data))
        print(f"OCR processing failed for {document_id}: {exc}")
        return {"document_id": document_id, "status": "failed", "reason": str(exc)}
