import logging
import os
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

log = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

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

_CATEGORY_RULES: dict[str, list[str]] = {
    "groceries": [
        "tesco", "sainsbury", "sainsburys", "lidl", "aldi", "asda", "morrisons",
        "waitrose", "co-op", "coop", "iceland", "ocado", "marks spencer food",
        "m&s food", "farmfoods",
    ],
    "transport": [
        "tfl", "trainline", "uber", "bolt", "gett", "lyft", "addison lee",
        "national rail", "scotrail", "great western", "avanti", "lner",
        "megabus", "national express", "flixbus",
    ],
    "fuel": [
        "shell", "bp", "esso", "texaco", "total", "jet", "murco",
        "sainsburys fuel", "tesco fuel", "asda fuel", "morrisons fuel",
    ],
    "food_and_drink": [
        "pret", "costa", "starbucks", "greggs", "mcdonalds", "burger king",
        "kfc", "nandos", "pizza hut", "dominos", "subway", "leon",
        "wasabi", "itsu", "eat", "caffe nero", "joe the juice",
    ],
    "subscriptions": [
        "netflix", "spotify", "amazon prime", "disney plus", "apple",
        "youtube premium", "adobe", "microsoft 365", "google one",
        "dropbox", "notion", "slack", "zoom", "canva",
    ],
    "utilities": [
        "british gas", "edf", "eon", "octopus energy", "bulb", "ovo",
        "thames water", "united utilities", "bt broadband", "virgin media",
        "sky", "talktalk", "plusnet", "ee", "three", "vodafone", "o2",
    ],
    "insurance": [
        "aviva", "direct line", "admiral", "axa", "zurich", "legal general",
        "simply business", "hiscox", "rias", "churchill", "more than",
    ],
    "office_supplies": [
        "staples", "viking", "ryman", "office depot", "amazon business",
        "currys business", "dell", "apple store",
    ],
    "professional_services": [
        "accountant", "solicitor", "lawyer", "legal", "consulting",
        "fiverr", "upwork", "peopleperhour",
    ],
    "advertising": [
        "google ads", "facebook ads", "meta ads", "instagram", "linkedin",
        "twitter ads", "tiktok ads", "mailchimp", "hubspot",
    ],
    "rent": [
        "rent", "lease", "landlord", "letting agent", "openrent",
    ],
    "travel": [
        "booking.com", "airbnb", "hotels.com", "expedia", "skyscanner",
        "easyjet", "ryanair", "british airways", "jet2", "wizz air",
        "tui", "premier inn", "travelodge",
    ],
    "income": [
        "salary", "wages", "payment received", "bank transfer in",
        "client payment", "invoice payment", "freelance",
    ],
    "tax": [
        "hmrc", "self assessment", "vat payment", "national insurance",
        "corporation tax", "paye",
    ],
    "health": [
        "pharmacy", "boots", "superdrug", "dentist", "optician",
        "specsavers", "bupa", "vitality",
    ],
    "home_office": [
        "ikea", "argos furniture", "john lewis", "desk", "chair",
        "monitor", "keyboard", "webcam", "headset",
    ],
}

_VALID_CATEGORIES = set(_CATEGORY_RULES.keys()) | {
    "transport", "fuel", "mileage", "office_supplies", "professional_fees",
    "legal", "accounting", "advertising", "marketing", "insurance",
    "utilities", "rent", "home_office", "phone", "internet", "training",
    "equipment", "tools", "software", "bank_charges", "staff_costs",
    "cost_of_goods", "pension",
}

_LLM_SYSTEM = (
    "You are a UK transaction categorizer for a self-employed tax tool. "
    "Given a bank transaction description, return ONLY a single category slug from this list: "
    + ", ".join(sorted(_VALID_CATEGORIES))
    + ". If none fits, return 'other'. Return only the slug, no explanation."
)


def suggest_category_from_rules(description: str) -> Optional[str]:
    """Categorize transaction by matching merchant name against UK rules database."""
    desc_lower = description.lower().strip()
    best_match: Optional[str] = None
    best_match_len = 0
    for category, merchants in _CATEGORY_RULES.items():
        for merchant in merchants:
            if merchant in desc_lower and len(merchant) > best_match_len:
                best_match = category
                best_match_len = len(merchant)
    return best_match


def _llm_categorize(description: str) -> Optional[str]:
    """GPT fallback when rules don't match."""
    if not OPENAI_API_KEY:
        return None
    try:
        import openai  # type: ignore[import-untyped]
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _LLM_SYSTEM},
                {"role": "user",   "content": description[:200]},
            ],
            max_tokens=20,
            temperature=0,
        )
        slug = (resp.choices[0].message.content or "").strip().lower().replace(" ", "_")
        return slug if slug in _VALID_CATEGORIES else None
    except Exception as exc:
        log.debug("LLM categorize failed: %s", exc)
        return None


@app.post("/categorize", response_model=CategorizationResponse)
async def categorize_transaction(
    request: CategorizationRequest,
    _user_id: str = Depends(get_current_user_id),
):
    """Rules first, GPT-4o-mini fallback for unknown vendors."""
    category = suggest_category_from_rules(request.description)
    if category is None:
        category = _llm_categorize(request.description)
    return CategorizationResponse(category=category)


class BulkCategorizationRequest(BaseModel):
    descriptions: list[str]

class BulkCategorizationResponse(BaseModel):
    results: list[dict]

@app.post("/categorize/bulk", response_model=BulkCategorizationResponse)
async def categorize_bulk(
    request: BulkCategorizationRequest,
    _user_id: str = Depends(get_current_user_id),
):
    """Categorize multiple transactions at once"""
    results = []
    for desc in request.descriptions:
        category = suggest_category_from_rules(desc)
        results.append({"description": desc, "category": category})
    return BulkCategorizationResponse(results=results)


@app.get("/categories")
async def list_categories():
    """List all available categories with merchant examples"""
    return {
        category: {"merchant_count": len(merchants), "examples": merchants[:5]}
        for category, merchants in _CATEGORY_RULES.items()
    }
