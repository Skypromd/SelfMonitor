from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Categorization Service",
    description="Suggests categories for transactions.",
    version="1.0.0"
)

class CategorizationRequest(BaseModel):
    description: str

class CategorizationResponse(BaseModel):
    category: Optional[str]

# This is a placeholder for a real ML model.
# It uses simple rules to categorize transactions.
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
async def categorize_transaction(request: CategorizationRequest):
    """
    Takes a transaction description and returns a suggested category.
    """
    category = suggest_category_from_rules(request.description)
    return CategorizationResponse(category=category)
