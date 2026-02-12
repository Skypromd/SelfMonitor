import os
import sys
import uuid
import datetime
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, status
from pydantic import BaseModel, Field

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

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
    user_id: str = Depends(get_current_user_id)
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
