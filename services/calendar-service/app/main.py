import datetime
import os
import sqlite3
import threading
import uuid
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

app = FastAPI(
    title="Calendar Service",
    description="Manages calendar events and reminders for users."
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# --- Security ---
AUTH_SECRET_KEY = os.environ["AUTH_SECRET_KEY"]
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


# --- Persistent event store ---
CALENDAR_DB_PATH = os.getenv("CALENDAR_DB_PATH", "/tmp/calendar.db")
db_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(CALENDAR_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_calendar_db() -> None:
    with db_lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()


def reset_calendar_db_for_tests() -> None:
    with db_lock:
        conn = _connect()
        conn.execute("DELETE FROM calendar_events")
        conn.commit()
        conn.close()


class CalendarEventCreate(BaseModel):
    user_id: str
    event_title: str
    event_date: datetime.date
    notes: Optional[str] = None


class CalendarEventRecord(CalendarEventCreate):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))


def _row_to_event(row: sqlite3.Row) -> CalendarEventRecord:
    return CalendarEventRecord(
        id=uuid.UUID(row["id"]),
        user_id=row["user_id"],
        event_title=row["event_title"],
        event_date=datetime.date.fromisoformat(row["event_date"]),
        notes=row["notes"],
        created_at=datetime.datetime.fromisoformat(row["created_at"]),
    )


def create_event(event: CalendarEventRecord) -> None:
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO calendar_events (id, user_id, event_title, event_date, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.id),
                    event.user_id,
                    event.event_title,
                    event.event_date.isoformat(),
                    event.notes,
                    event.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def list_events(
    user_id: str,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
) -> List[CalendarEventRecord]:
    query = "SELECT * FROM calendar_events WHERE user_id = ?"
    params: list[object] = [user_id]

    if start_date:
        query += " AND event_date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND event_date <= ?"
        params.append(end_date.isoformat())

    query += " ORDER BY event_date ASC, created_at ASC"

    with db_lock:
        conn = _connect()
        try:
            rows = conn.execute(query, tuple(params)).fetchall()
        finally:
            conn.close()
    return [_row_to_event(row) for row in rows]


@app.post("/events", response_model=CalendarEventRecord, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    event: CalendarEventCreate,
    current_user_id: str = Depends(get_current_user_id),
):
    if event.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden user scope")

    record = CalendarEventRecord(**event.model_dump())
    create_event(record)
    return record


@app.get("/events", response_model=List[CalendarEventRecord])
async def get_my_calendar_events(
    start_date: Optional[datetime.date] = Query(default=None),
    end_date: Optional[datetime.date] = Query(default=None),
    current_user_id: str = Depends(get_current_user_id),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")
    return list_events(current_user_id, start_date, end_date)


init_calendar_db()
