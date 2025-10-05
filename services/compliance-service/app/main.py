from fastapi import FastAPI, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from . import crud, models, schemas
from .database import get_db

app = FastAPI(
    title="Compliance Service",
    description="Handles audit logs and other compliance tasks.",
    version="1.0.0"
)

# --- Endpoints ---
@app.post("/audit-events", response_model=schemas.AuditEvent, status_code=status.HTTP_201_CREATED)
async def record_audit_event(
    event: schemas.AuditEventCreate,
    db: AsyncSession = Depends(get_db)
):
    """Records a new event in the persistent audit log."""
    db_event = await crud.create_audit_event(db=db, event=event)
    return db_event

@app.get("/audit-events", response_model=List[schemas.AuditEvent])
async def query_audit_events(
    user_id: Optional[str] = Query(None, description="Filter events by user ID."),
    db: AsyncSession = Depends(get_db)
):
    """Queries the audit log from the database."""
    # Note: entity_id search is removed for simplicity. A real implementation
    # would use JSONB queries to search the 'details' field.
    events = await crud.query_audit_events(db=db, user_id=user_id)
    return events
