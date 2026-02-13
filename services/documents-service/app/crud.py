from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
import uuid
from typing import List
import datetime

from .expense_classifier import to_expense_article

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

    extracted_dict = dict(db_document.extracted_data or {})
    changed_fields = False

    if payload.total_amount is not None:
        extracted_dict["total_amount"] = payload.total_amount
        changed_fields = True
    if payload.vendor_name is not None:
        extracted_dict["vendor_name"] = payload.vendor_name
        changed_fields = True
    if payload.transaction_date is not None:
        extracted_dict["transaction_date"] = payload.transaction_date.isoformat()
        changed_fields = True
    if payload.suggested_category is not None:
        extracted_dict["suggested_category"] = payload.suggested_category
        changed_fields = True
    if payload.expense_article is not None:
        extracted_dict["expense_article"] = payload.expense_article
        changed_fields = True
    if payload.is_potentially_deductible is not None:
        extracted_dict["is_potentially_deductible"] = payload.is_potentially_deductible
        changed_fields = True

    if payload.suggested_category is not None and payload.expense_article is None and payload.is_potentially_deductible is None:
        expense_article, deductible = to_expense_article(payload.suggested_category)
        extracted_dict["expense_article"] = expense_article
        extracted_dict["is_potentially_deductible"] = deductible

    status = payload.review_status
    if status == "confirmed" and changed_fields:
        status = "corrected"
    extracted_dict["review_status"] = status
    extracted_dict["needs_review"] = False
    extracted_dict["reviewed_at"] = datetime.datetime.now(datetime.UTC).isoformat()
    if payload.review_notes is not None:
        extracted_dict["review_notes"] = payload.review_notes

    db_document.extracted_data = extracted_dict
    await db.commit()
    await db.refresh(db_document)
    return db_document
