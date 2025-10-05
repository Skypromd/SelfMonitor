from fastapi import FastAPI
from pydantic import BaseModel
import datetime

app = FastAPI(
    title="Calendar Service",
    description="Manages calendar events and reminders for users."
)

class CalendarEvent(BaseModel):
    user_id: str
    event_title: str
    event_date: datetime.date
    notes: str | None = None

@app.post("/events")
async def create_calendar_event(event: CalendarEvent):
    """
    In a real app, this would connect to Google Calendar/Outlook API
    using user's OAuth2 credentials and create a real event.
    For now, we just log it to the console.
    """
    print("="*30)
    print("📅 CALENDAR EVENT CREATED 📅")
    print(f"User: {event.user_id}")
    print(f"Date: {event.event_date}")
    print(f"Title: {event.event_title}")
    print(f"Notes: {event.notes or 'N/A'}")
    print("="*30)
    return {"message": "Calendar event created successfully (simulated)."}
