import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
import datetime

app = FastAPI(
    title="Calendar Service",
    description="Manages calendar events and reminders for users."
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


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


class CalendarEvent(BaseModel):
    user_id: str
    event_title: str
    event_date: datetime.date
    notes: str | None = None

@app.post("/events")
async def create_calendar_event(
    event: CalendarEvent,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    In a real app, this would connect to Google Calendar/Outlook API
    using user's OAuth2 credentials and create a real event.
    For now, we just log it to the console.
    """
    if event.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden user scope")

    print("="*30)
    print("📅 CALENDAR EVENT CREATED 📅")
    print(f"User: {event.user_id}")
    print(f"Date: {event.event_date}")
    print(f"Title: {event.event_title}")
    print(f"Notes: {event.notes or 'N/A'}")
    print("="*30)
    return {"message": "Calendar event created successfully (simulated)."}
