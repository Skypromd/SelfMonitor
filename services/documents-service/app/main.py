import datetime
import logging
import os

# --- Helpers ---
import re
import sys
import uuid
from pathlib import Path
from typing import List

import boto3  # type: ignore[import-untyped]
import httpx
from botocore.client import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_http.request_id import RequestIdMiddleware, get_request_id

from . import crud, schemas
from .celery_app import ocr_processing_task
from .database import get_db


def _sanitize_filename(filename: str) -> str:
    """Strip path components and dangerous characters from a filename."""
    # Take only the base name
    filename = os.path.basename(filename.replace("\\", "/"))
    # Remove null bytes and control characters
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    # Replace characters that are problematic on filesystems or in URLs
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    return filename.strip()


# --- File Upload Validation ---
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".txt",
}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "text/plain",
}

# --- S3 Configuration ---
TRANSACTIONS_SERVICE_URL = os.getenv(
    "TRANSACTIONS_SERVICE_URL",
    "http://transactions-service/transactions/receipt-drafts",
)


def _receipt_drafts_base_url() -> str:
    raw = (TRANSACTIONS_SERVICE_URL or "").strip().rstrip("/")
    if raw.endswith("/transactions/receipt-drafts"):
        return raw
    return f"{raw}/transactions/receipt-drafts"


def _parse_extracted_total(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _parse_extracted_transaction_date(raw: object) -> datetime.date | None:
    if raw is None:
        return None
    if isinstance(raw, datetime.datetime):
        return raw.date()
    if isinstance(raw, datetime.date):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return datetime.date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_extracted_vat(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "documents-bucket")
# For local development with LocalStack, boto3 needs the endpoint_url.
S3_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")

# Configure boto3 client
s3_client = boto3.client(
    "s3", endpoint_url=S3_ENDPOINT_URL, config=Config(signature_version="s3v4")
)

app = FastAPI(
    title="Documents Service",
    description="Handles document uploads, orchestrates OCR processing, and stores extracted data.",
    version="1.0.0",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.0.248:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from libs.shared_auth.jwt_fastapi import (  # noqa: E402,I001,I002,C0411
    build_jwt_auth_dependencies,
)
from libs.shared_auth.plan_enforcement_log import log_plan_enforcement_denial  # noqa: E402
from libs.shared_auth.plan_limits import PlanLimits, get_plan_limits  # noqa: E402
from libs.shared_http.request_id import get_request_id  # noqa: E402

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()
OCR_REVIEW_COMPLETION_SECONDS = Histogram(
    "ocr_review_completion_seconds",
    "Time from document upload to review completion.",
    buckets=(60, 120, 300, 600, 1800, 3600, 7200, 21600, 43200, 86400, float("inf")),
)
OCR_MANUAL_OVERRIDES_TOTAL = Counter(
    "ocr_manual_overrides_total",
    "Total OCR manual overrides by review status.",
    labelnames=("review_status",),
)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            {
                "status": "degraded",
                "database": "unreachable",
                "detail": str(exc)[:240],
            },
            status_code=503,
        )
    return {"status": "ok", "database": "connected"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/documents/upload",
    response_model=schemas.Document,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
    limits: PlanLimits = Depends(get_plan_limits),
    db: AsyncSession = Depends(get_db),
):
    """Accepts a document, uploads it to S3, creates a DB record, and triggers OCR."""
    # --- Filename sanitization ---
    raw_filename = file.filename or ""
    safe_filename = _sanitize_filename(raw_filename)
    if not safe_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename"
        )

    # --- File extension validation ---
    file_extension = os.path.splitext(safe_filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{file_extension}' is not allowed. Allowed: {allowed}",
        )

    # --- Content-type validation ---
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type '{content_type}' is not allowed.",
        )

    # --- File size validation ---
    contents = await file.read()
    file_len = len(contents)
    if file_len > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.",
        )

    limit_bytes = limits.storage_limit_gb * (1024**3)
    used_bytes = await crud.total_file_size_bytes_for_user(db, user_id=user_id)
    if used_bytes + file_len > limit_bytes:
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=limits.plan,
            feature="storage_bytes",
            reason="storage_quota_exceeded",
            current=used_bytes + file_len,
            limit_value=limit_bytes,
            request_id=get_request_id(),
            compliance_bearer_token=bearer_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Storage quota exceeded for plan '{limits.plan}' "
                f"({limits.storage_limit_gb} GB). Remove documents or upgrade."
            ),
        )

    doc_count = await crud.count_documents_for_user(db, user_id=user_id)
    if limits.documents_max_count > 0 and doc_count >= limits.documents_max_count:
        log_plan_enforcement_denial(
            user_id=user_id,
            plan=limits.plan,
            feature="documents_count",
            reason="document_cap_exceeded",
            current=doc_count,
            limit_value=limits.documents_max_count,
            request_id=get_request_id(),
            compliance_bearer_token=bearer_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Document count limit reached for plan '{limits.plan}' "
                f"({limits.documents_max_count}). Remove documents or upgrade."
            ),
        )

    await file.seek(0)

    s3_key = f"{user_id}/{uuid.uuid4()}{file_extension}"

    try:
        s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, s3_key)
    except ClientError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload file to S3: {e}"
        ) from e

    db_document = await crud.create_document(
        db,
        user_id=user_id,
        filename=safe_filename,
        filepath=s3_key,
        file_size_bytes=file_len,
    )

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
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists all documents for the authenticated user from the database."""
    return await crud.get_documents_by_user(db, user_id=user_id, skip=skip, limit=limit)


@app.get("/documents/review-queue", response_model=schemas.DocumentReviewQueueResponse)
async def list_documents_review_queue(
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    total, items = await crud.list_documents_requiring_review(
        db,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return schemas.DocumentReviewQueueResponse(
        total=total,
        items=[schemas.Document.model_validate(item) for item in items],
    )


@app.get("/documents/{document_id}", response_model=schemas.Document)
async def get_document(
    document_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves metadata for a specific document."""
    db_document = await crud.get_document_by_id(db, user_id=user_id, doc_id=document_id)
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return db_document


@app.patch("/documents/{document_id}/review", response_model=schemas.Document)
async def review_document(
    document_id: uuid.UUID,
    payload: schemas.DocumentReviewUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    bearer: str = Depends(get_bearer_token),
    db: AsyncSession = Depends(get_db),
):
    updated = await crud.update_document_review(
        db,
        user_id=user_id,
        doc_id=document_id,
        payload=payload,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    uploaded_at = getattr(updated, "uploaded_at", None)
    if isinstance(uploaded_at, datetime.datetime):
        elapsed_seconds = (
            datetime.datetime.now(datetime.UTC) - uploaded_at
        ).total_seconds()
        if elapsed_seconds >= 0:
            OCR_REVIEW_COMPLETION_SECONDS.observe(elapsed_seconds)

    extracted_data_raw = getattr(updated, "extracted_data", None)
    extracted_data = extracted_data_raw if isinstance(extracted_data_raw, dict) else {}
    review_status = str(extracted_data.get("review_status") or "").strip().lower()
    if review_status in {"corrected", "ignored"}:
        OCR_MANUAL_OVERRIDES_TOTAL.labels(review_status=review_status).inc()

    draft_id = extracted_data.get("receipt_draft_transaction_id")
    if review_status in {"confirmed", "corrected"} and not draft_id:
        parsed_total = _parse_extracted_total(extracted_data.get("total_amount"))
        parsed_date = _parse_extracted_transaction_date(
            extracted_data.get("transaction_date")
        )
        if parsed_total is not None and parsed_date is not None:
            body: dict = {
                "document_id": str(document_id),
                "filename": updated.filename,
                "transaction_date": parsed_date.isoformat(),
                "total_amount": parsed_total,
                "currency": "GBP",
            }
            vendor_name = extracted_data.get("vendor_name")
            if isinstance(vendor_name, str) and vendor_name.strip():
                body["vendor_name"] = vendor_name.strip()
            suggested = extracted_data.get("suggested_category")
            if isinstance(suggested, str) and suggested.strip():
                body["suggested_category"] = suggested.strip()
            expense_article = extracted_data.get("expense_article")
            if isinstance(expense_article, str) and expense_article.strip():
                body["expense_article"] = expense_article.strip()
            deductible = extracted_data.get("is_potentially_deductible")
            if isinstance(deductible, bool):
                body["is_potentially_deductible"] = deductible
            vat_parsed = _parse_extracted_vat(extracted_data.get("vat_amount_gbp"))
            if vat_parsed is not None and vat_parsed > 0:
                body["vat_amount_gbp"] = vat_parsed
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        _receipt_drafts_base_url(),
                        json=body,
                        headers={"Authorization": f"Bearer {bearer}"},
                    )
                    response.raise_for_status()
                    response_payload = response.json()
            except Exception as exc:
                logger.warning(
                    "receipt draft create after review failed request_id=%s doc_id=%s: %s",
                    get_request_id(),
                    document_id,
                    exc,
                    exc_info=True,
                )
            else:
                if isinstance(response_payload, dict):
                    transaction = response_payload.get("transaction")
                    duplicated = response_payload.get("duplicated")
                    new_tid = (
                        transaction.get("id")
                        if isinstance(transaction, dict)
                        else None
                    )
                    if new_tid:
                        merged = await crud.patch_document_extracted_fields(
                            db,
                            user_id=user_id,
                            doc_id=document_id,
                            fields={
                                "receipt_draft_transaction_id": str(new_tid),
                                "receipt_draft_duplicated": bool(duplicated)
                                if duplicated is not None
                                else False,
                            },
                        )
                        if merged is not None:
                            updated = merged
                            extracted_data = dict(merged.extracted_data or {})
                            draft_id = extracted_data.get("receipt_draft_transaction_id")

    if draft_id and review_status in {"corrected", "confirmed"}:
        update_body: dict = {}
        if payload.total_amount is not None:
            update_body["total_amount"] = payload.total_amount
        if payload.vendor_name is not None:
            update_body["vendor_name"] = payload.vendor_name
        if payload.transaction_date is not None:
            update_body["transaction_date"] = str(payload.transaction_date)
        if payload.suggested_category is not None:
            update_body["suggested_category"] = payload.suggested_category
        if payload.vat_amount_gbp is not None:
            update_body["vat_amount_gbp"] = payload.vat_amount_gbp
        if update_body:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.patch(
                        f"{_receipt_drafts_base_url()}/{draft_id}",
                        json=update_body,
                        headers={"Authorization": f"Bearer {bearer}"},
                    )
            except Exception as exc:
                logger.warning(
                    "receipt draft sync failed request_id=%s draft_id=%s: %s",
                    get_request_id(),
                    draft_id,
                    exc,
                    exc_info=True,
                )

    return updated
