from fastapi import FastAPI, Depends, status
from pydantic import BaseModel, Field
from typing import Literal
import uuid
import datetime

# --- Placeholder Security ---

def fake_auth_check() -> str:
    """A fake dependency to simulate user authentication and return a user ID."""
    return "fake-user-123"

app = FastAPI(
    title="Integrations Service",
    description="Facades external API integrations.",
    version="1.0.0"
)

# --- Models ---

class HMRCSubmissionRequest(BaseModel):
    tax_period_start: datetime.date
    tax_period_end: datetime.date
    tax_due: float

class SubmissionStatus(BaseModel):
    submission_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: Literal['pending', 'completed', 'failed']
    message: str

# --- Endpoints ---

@app.post(
    "/integrations/hmrc/submit-tax-return",
    response_model=SubmissionStatus,
    status_code=status.HTTP_202_ACCEPTED
)
async def submit_tax_return(
    request: HMRCSubmissionRequest, 
    user_id: str = Depends(fake_auth_check)
):
    """
    Simulates submitting a tax return to an external service like HMRC.

    In a real app, this would:
    1. Authenticate with the external service's API.
    2. Format the data into the required payload.
    3. Make the API call, handling potential errors and retries.
    4. Store the submission ID and status for later polling.
    """
    print(f"User {user_id} is submitting a tax return for the period {request.tax_period_start} to {request.tax_period_end}.")
    print(f"Calling external HMRC API with tax due: {request.tax_due}")

    # Simulate the external service accepting the request
    return SubmissionStatus(
        status='pending',
        message='Your submission has been received by HMRC and is being processed.'
    )
