import os
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .database import get_db

app = FastAPI(
    title="Compliance Service",
    description="Handles audit logs and other compliance tasks.",
    version="1.0.0"
)

# --- Security ---
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


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

# --- Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/audit-events", response_model=schemas.AuditEvent, status_code=status.HTTP_201_CREATED)
async def record_audit_event(
    event: schemas.AuditEventCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Records a new event in the persistent audit log."""
    if event.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden user scope")
    db_event = await crud.create_audit_event(db=db, event=event)
    return db_event

@app.get("/audit-events", response_model=List[schemas.AuditEvent])
async def query_audit_events(
    user_id: Optional[str] = Query(None, description="Filter events by user ID."),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Queries the audit log from the database."""
    if user_id and user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden user scope")

    # Note: entity_id search is removed for simplicity. A real implementation
    # would use JSONB queries to search the 'details' field.
    target_user_id = user_id or current_user_id
    events = await crud.query_audit_events(db=db, user_id=target_user_id)
    return events
