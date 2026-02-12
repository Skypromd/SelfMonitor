from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
import uuid
from typing import List

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

async def update_document_with_ocr_results(db: AsyncSession, doc_id: str, status: str, extracted_data: schemas.ExtractedData):
    """Updates a document's status and extracted data after OCR processing."""
    doc_uuid = uuid.UUID(doc_id)
    result = await db.execute(select(models.Document).filter(models.Document.id == doc_uuid))
    db_document = result.scalars().first()
    if db_document:
        db_document.status = status
        db_document.extracted_data = extracted_data.model_dump()
        await db.commit()
    return db_document
