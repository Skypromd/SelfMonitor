import os
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
import uuid
import datetime

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
