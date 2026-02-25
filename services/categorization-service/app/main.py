import os
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

app = FastAPI(
    title="Categorization Service",
    description="Suggests categories for transactions.",
    version="1.0.0"
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


class CategorizationRequest(BaseModel):
    description: str

class CategorizationResponse(BaseModel):
    category: Optional[str]

# Deterministic ruleset used as the baseline categorization model.
def suggest_category_from_rules(description: str) -> Optional[str]:
    """A simple rule-based model to categorize a transaction."""
    desc_lower = description.lower()

    if "tesco" in desc_lower or "sainsbury" in desc_lower or "lidl" in desc_lower or "asda" in desc_lower:
        return "groceries"
    if "tfl" in desc_lower or "trainline" in desc_lower or "uber" in desc_lower:
        return "transport"
    if "pret" in desc_lower or "costa" in desc_lower or "starbucks" in desc_lower:
        return "food_and_drink"
    if "amazon prime" in desc_lower or "netflix" in desc_lower or "spotify" in desc_lower:
        return "subscriptions"
    if "salary" in desc_lower or "payment" in desc_lower:
        return "income"

    return None # If no rule matches

@app.post("/categorize", response_model=CategorizationResponse)
async def categorize_transaction(
    request: CategorizationRequest,
    _user_id: str = Depends(get_current_user_id),
):
    """
    Takes a transaction description and returns a suggested category.
    """
    category = suggest_category_from_rules(request.description)
    return CategorizationResponse(category=category)
