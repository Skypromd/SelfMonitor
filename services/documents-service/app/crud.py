from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
import uuid
from typing import List
import datetime
import re

from .expense_classifier import to_expense_article

_REVIEW_TRACKED_FIELDS: tuple[str, ...] = (
    "total_amount",
    "vendor_name",
    "transaction_date",
    "suggested_category",
    "expense_article",
    "is_potentially_deductible",
)
_FEEDBACK_FIELDS: tuple[str, ...] = (
    "suggested_category",
    "expense_article",
    "is_potentially_deductible",
)

async def create_document(db: AsyncSession, user_id: str, filename: str, filepath: str) -> models.Document:
    db_document = models.Document(user_id=user_id, filename=filename, filepath=filepath)
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    return db_document

async def get_documents_by_user(db: AsyncSession, user_id: str) -> List[models.Document]:
    result = await db.execute(
        select(models.Document)
        .filter(models.Document.user_id == user_id)
        .order_by(models.Document.uploaded_at.desc())
    )
    return result.scalars().all()

async def get_document_by_id(db: AsyncSession, user_id: str, doc_id: uuid.UUID) -> models.Document | None:
    result = await db.execute(
        select(models.Document)
        .filter(models.Document.id == doc_id, models.Document.user_id == user_id)
    )
    return result.scalars().first()


async def get_document_for_processing(db: AsyncSession, doc_id: str) -> models.Document | None:
    doc_uuid = uuid.UUID(doc_id)
    result = await db.execute(select(models.Document).filter(models.Document.id == doc_uuid))
    return result.scalars().first()


async def update_document_with_ocr_results(db: AsyncSession, doc_id: str, status: str, extracted_data: schemas.ExtractedData):
    """Updates a document's status and extracted data after OCR processing."""
    db_document = await get_document_for_processing(db, doc_id=doc_id)
    if db_document:
        db_document.status = status
        db_document.extracted_data = extracted_data.model_dump(mode="json")
        await db.commit()
    return db_document


def _normalize_vendor_key(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return normalized or None


def _normalize_review_value(field: str, value: object) -> float | str | bool | None:
    if value is None:
        return None
    if field == "transaction_date":
        if isinstance(value, datetime.date):
            return value.isoformat()
        if isinstance(value, str):
            stripped = value.strip()
            return stripped.split("T", 1)[0] if stripped else None
    if field == "total_amount":
        if isinstance(value, (int, float)):
            return round(float(value), 2)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                return round(float(stripped), 2)
            except ValueError:
                return stripped
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return str(value)


def _build_review_changes(
    *,
    before_data: dict[str, object],
    after_data: dict[str, object],
) -> dict[str, dict[str, float | str | bool | None]]:
    changes: dict[str, dict[str, float | str | bool | None]] = {}
    for field in _REVIEW_TRACKED_FIELDS:
        before_value = _normalize_review_value(field, before_data.get(field))
        after_value = _normalize_review_value(field, after_data.get(field))
        if before_value == after_value:
            continue
        changes[field] = {
            "before": before_value,
            "after": after_value,
        }
    return changes


async def get_latest_category_feedback_for_vendor(
    db: AsyncSession,
    *,
    user_id: str,
    vendor_name: str | None,
    scan_limit: int = 300,
) -> dict[str, str | bool] | None:
    vendor_key = _normalize_vendor_key(vendor_name)
    if vendor_key is None:
        return None

    result = await db.execute(
        select(models.Document)
        .filter(models.Document.user_id == user_id)
        .order_by(models.Document.uploaded_at.desc())
        .limit(scan_limit)
    )
    for document in result.scalars().all():
        extracted = document.extracted_data if isinstance(document.extracted_data, dict) else {}
        if extracted.get("review_status") != "corrected":
            continue
        feedback_vendor_key = _normalize_vendor_key(str(extracted.get("vendor_name") or ""))
        if feedback_vendor_key != vendor_key:
            continue

        review_changes = extracted.get("review_changes")
        if not isinstance(review_changes, dict):
            continue
        if not any(field in review_changes for field in _FEEDBACK_FIELDS):
            continue

        category = extracted.get("suggested_category")
        if not isinstance(category, str) or not category.strip():
            continue

        feedback: dict[str, str | bool] = {
            "suggested_category": category.strip(),
        }
        expense_article = extracted.get("expense_article")
        if isinstance(expense_article, str) and expense_article.strip():
            feedback["expense_article"] = expense_article.strip()
        deductible = extracted.get("is_potentially_deductible")
        if isinstance(deductible, bool):
            feedback["is_potentially_deductible"] = deductible
        feedback["feedback_source"] = "manual_review"
        return feedback
    return None


def _needs_review(document: models.Document) -> bool:
    extracted = document.extracted_data if isinstance(document.extracted_data, dict) else {}
    return bool(extracted.get("needs_review") is True)


async def list_documents_requiring_review(
    db: AsyncSession,
    *,
    user_id: str,
    limit: int = 25,
    offset: int = 0,
) -> tuple[int, list[models.Document]]:
    documents = await get_documents_by_user(db, user_id=user_id)
    review_documents = [document for document in documents if _needs_review(document)]
    total = len(review_documents)
    return total, review_documents[offset : offset + limit]


async def update_document_review(
    db: AsyncSession,
    *,
    user_id: str,
    doc_id: uuid.UUID,
    payload: schemas.DocumentReviewUpdateRequest,
) -> models.Document | None:
    db_document = await get_document_by_id(db, user_id=user_id, doc_id=doc_id)
    if db_document is None:
        return None

    original_extracted = dict(db_document.extracted_data or {})
    extracted_dict = dict(original_extracted)

    if payload.total_amount is not None:
        extracted_dict["total_amount"] = payload.total_amount
    if payload.vendor_name is not None:
        extracted_dict["vendor_name"] = payload.vendor_name
    if payload.transaction_date is not None:
        extracted_dict["transaction_date"] = payload.transaction_date.isoformat()
    if payload.suggested_category is not None:
        extracted_dict["suggested_category"] = payload.suggested_category
    if payload.expense_article is not None:
        extracted_dict["expense_article"] = payload.expense_article
    if payload.is_potentially_deductible is not None:
        extracted_dict["is_potentially_deductible"] = payload.is_potentially_deductible

    if payload.suggested_category is not None and payload.expense_article is None and payload.is_potentially_deductible is None:
        expense_article, deductible = to_expense_article(payload.suggested_category)
        extracted_dict["expense_article"] = expense_article
        extracted_dict["is_potentially_deductible"] = deductible

    review_changes = _build_review_changes(before_data=original_extracted, after_data=extracted_dict)
    changed_fields = bool(review_changes)

    status = payload.review_status
    if status == "confirmed" and changed_fields:
        status = "corrected"
    extracted_dict["review_status"] = status
    extracted_dict["needs_review"] = False
    extracted_dict["reviewed_at"] = datetime.datetime.now(datetime.UTC).isoformat()
    if changed_fields:
        extracted_dict["review_changes"] = review_changes
    if payload.review_notes is not None:
        extracted_dict["review_notes"] = payload.review_notes

    db_document.extracted_data = extracted_dict
    await db.commit()
    await db.refresh(db_document)
    return db_document
