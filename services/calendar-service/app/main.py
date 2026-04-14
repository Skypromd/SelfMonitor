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


def migrate_calendar_db() -> None:
    """Add new columns to existing DB; safe to run on every startup."""
    new_columns = [
        "ALTER TABLE calendar_events ADD COLUMN event_time TEXT",
        "ALTER TABLE calendar_events ADD COLUMN category TEXT NOT NULL DEFAULT 'personal'",
        "ALTER TABLE calendar_events ADD COLUMN is_completed INTEGER NOT NULL DEFAULT 0",
    ]
    with db_lock:
        conn = _connect()
        try:
            for sql in new_columns:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass  # column already exists
            conn.commit()
        finally:
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
    event_time: Optional[str] = None      # "HH:MM"
    category: str = "personal"            # hmrc | invoice | meeting | personal | other
    is_completed: bool = False


class CalendarEventUpdate(BaseModel):
    event_title: Optional[str] = None
    event_date: Optional[datetime.date] = None
    notes: Optional[str] = None
    event_time: Optional[str] = None
    category: Optional[str] = None
    is_completed: Optional[bool] = None


class CalendarEventRecord(CalendarEventCreate):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


def _row_to_event(row: sqlite3.Row) -> CalendarEventRecord:
    keys = row.keys()
    return CalendarEventRecord(
        id=uuid.UUID(row["id"]),
        user_id=row["user_id"],
        event_title=row["event_title"],
        event_date=datetime.date.fromisoformat(row["event_date"]),
        notes=row["notes"],
        event_time=row["event_time"] if "event_time" in keys else None,
        category=row["category"] if "category" in keys else "personal",
        is_completed=bool(row["is_completed"]) if "is_completed" in keys else False,
        created_at=datetime.datetime.fromisoformat(row["created_at"]),
    )


def create_event(event: CalendarEventRecord) -> None:
    with db_lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO calendar_events
                  (id, user_id, event_title, event_date, notes, created_at,
                   event_time, category, is_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.id),
                    event.user_id,
                    event.event_title,
                    event.event_date.isoformat(),
                    event.notes,
                    event.created_at.isoformat(),
                    event.event_time,
                    event.category,
                    int(event.is_completed),
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


def get_event_by_id(event_id: str) -> Optional[CalendarEventRecord]:
    with db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM calendar_events WHERE id = ?", (event_id,)
            ).fetchone()
        finally:
            conn.close()
    return _row_to_event(row) if row else None


def update_event(event_id: str, upd: CalendarEventUpdate) -> Optional[CalendarEventRecord]:
    fields: list[str] = []
    params: list[object] = []

    if upd.event_title is not None:
        fields.append("event_title = ?"); params.append(upd.event_title)
    if upd.event_date is not None:
        fields.append("event_date = ?"); params.append(upd.event_date.isoformat())
    if upd.notes is not None:
        fields.append("notes = ?"); params.append(upd.notes)
    if upd.event_time is not None:
        fields.append("event_time = ?"); params.append(upd.event_time)
    if upd.category is not None:
        fields.append("category = ?"); params.append(upd.category)
    if upd.is_completed is not None:
        fields.append("is_completed = ?"); params.append(int(upd.is_completed))

    if fields:
        params.append(event_id)
        with db_lock:
            conn = _connect()
            try:
                conn.execute(
                    f"UPDATE calendar_events SET {', '.join(fields)} WHERE id = ?",
                    tuple(params),
                )
                conn.commit()
            finally:
                conn.close()

    return get_event_by_id(event_id)


def delete_event_by_id(event_id: str) -> None:
    with db_lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
            conn.commit()
        finally:
            conn.close()


@app.post("/events", response_model=CalendarEventRecord, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    event: CalendarEventCreate,
    current_user_id: str = Depends(get_current_user_id),
):
    if event.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden user scope")

    if event.event_date.year < 2020:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event date cannot be before 2020")
    if event.event_date.year > 2100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event date cannot be after 2100")

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


@app.put("/events/{event_id}", response_model=CalendarEventRecord)
async def update_calendar_event(
    event_id: str,
    upd: CalendarEventUpdate,
    current_user_id: str = Depends(get_current_user_id),
):
    event = get_event_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    updated = update_event(event_id, upd)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")
    return updated


@app.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_event(
    event_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    event = get_event_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    delete_event_by_id(event_id)


@app.patch("/events/{event_id}/complete", response_model=CalendarEventRecord)
async def toggle_complete_calendar_event(
    event_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    event = get_event_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    updated = update_event(event_id, CalendarEventUpdate(is_completed=not event.is_completed))
    if updated is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")
    return updated


init_calendar_db()
migrate_calendar_db()
