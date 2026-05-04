import logging
import os
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .learn_store import lookup_user_category, upsert_rule
from .merchant_rules_store import (
    list_global_merchant_rules,
    lookup_global_merchant_category,
    upsert_global_merchant_rule,
)

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


class LearnRequest(BaseModel):
    description: str
    category: str


class LearnResponse(BaseModel):
    stored: bool
    pattern: Optional[str] = None


class InternalMerchantRuleRequest(BaseModel):
    pattern: str
    category: str


class InternalMerchantRuleResponse(BaseModel):
    stored: bool
    pattern: Optional[str] = None


class MerchantRulesListResponse(BaseModel):
    rules: dict[str, str]

_CATEGORY_RULES: dict[str, list[str]] = {
    "groceries": [
        "tesco", "sainsbury", "sainsburys", "lidl", "aldi", "asda", "morrisons",
        "waitrose", "co-op", "coop", "iceland", "ocado", "marks spencer food",
        "m&s food", "farmfoods", "budgens", "spar", "londis", "premier",
        "heron foods", "b&m", "home bargains", "poundland", "wilko",
    ],
    "transport": [
        "tfl", "trainline", "uber", "bolt", "gett", "lyft", "addison lee",
        "national rail", "scotrail", "great western", "avanti", "lner",
        "megabus", "national express", "flixbus", "black cab", "gettaxi",
        "free now", "voi", "lime", "santander cycles",
    ],
    "fuel": [
        "shell", "bp", "esso", "texaco", "total", "jet", "murco",
        "sainsburys fuel", "tesco fuel", "asda fuel", "morrisons fuel",
    ],
    "food_and_drink": [
        "pret", "costa", "starbucks", "greggs", "mcdonalds", "burger king",
        "kfc", "nandos", "pizza hut", "dominos", "subway", "leon",
        "wasabi", "itsu", "eat", "caffe nero", "joe the juice",
        "deliveroo", "uber eats", "just eat", "hungryhouse", "five guys",
        "wagamama", "zizzi", "ask italian", "franco manca", "honest burgers",
        "tortilla", "chipotle", "shake shack",
    ],
    "subscriptions": [
        "netflix", "spotify", "amazon prime", "disney plus", "apple",
        "youtube premium", "adobe", "microsoft 365", "google one",
        "dropbox", "notion", "slack", "zoom", "canva", "audible",
        "now tv", "nowtv", "paramount plus", "apple music", "deezer",
        "tidal", "strava", "peloton", "headspace", "calm",
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
        "specsavers", "bupa", "vitality", "lloyds pharmacy", "well pharmacy",
        "day lewis", "rowlands pharmacy", "nhs", "gp surgery",
    ],
    "home_office": [
        "ikea", "argos furniture", "john lewis", "desk", "chair",
        "monitor", "keyboard", "webcam", "headset",
        "currys", "pc world", "argos", "very.co.uk", "ao.com",
    ],
    "cost_of_goods": [
        "amazon.co.uk", "amazon uk", "amzn.co.uk", "amzn mktp",
        "ebay", "etsy uk", "etsy", "aliexpress", "wish.com",
        "book depository", "waterstones", "wh smith",
    ],
    "entertainment": [
        "cineworld", "odeon", "vue cinema", "everyman", "picturehouse",
        "ticketmaster", "seetickets", "dice.fm", "eventbrite",
        "gigsandtours", "axs", "stubhub",
    ],
    "software": [
        "github", "gitlab", "jetbrains", "figma", "linear.app",
        "monday.com", "asana", "trello", "atlassian", "jira",
        "vercel", "netlify", "heroku", "digitalocean", "amazon web services",
    ],
    "bank_charges": [
        "lloyds bank", "barclays", "hsbc uk", "hsbc", "natwest",
        "nationwide", "santander", "metro bank", "starling bank",
        "monzo", "revolut", "tsb bank", "halifax", "rbs", "royal bank",
        "coutts", "wise", "transferwise", "paypal fees",
    ],
    "tools": [
        "screwfix", "toolstation", "travis perkins", "wickes", "bnq",
        "b&q", "selco", "jewson", "halfords",
    ],
}

_VALID_CATEGORIES = set(_CATEGORY_RULES.keys()) | {
    "transport", "fuel", "mileage", "office_supplies", "professional_fees",
    "legal", "accounting", "advertising", "marketing", "insurance",
    "utilities", "rent", "home_office", "phone", "internet", "training",
    "equipment", "tools", "software", "bank_charges", "staff_costs",
    "cost_of_goods", "pension", "entertainment", "other",
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


def _resolve_category(user_id: str, description: str, *, use_llm: bool) -> Optional[str]:
    category = lookup_user_category(user_id, description)
    if category is not None:
        return category
    category = lookup_global_merchant_category(description)
    if category is not None:
        return category
    category = suggest_category_from_rules(description)
    if category is not None:
        return category
    if use_llm:
        return _llm_categorize(description)
    return None


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


@app.post("/learn", response_model=LearnResponse)
async def learn_category_rule(
    request: LearnRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Remember a description → category mapping for this user (applied before global rules)."""
    cat = request.category.strip().lower().replace(" ", "_")
    if cat not in _VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown category '{request.category}'.",
        )
    pattern = upsert_rule(user_id, request.description, cat)
    if pattern is None:
        return LearnResponse(stored=False, pattern=None)
    return LearnResponse(stored=True, pattern=pattern)


@app.get("/merchant-rules", response_model=MerchantRulesListResponse)
async def get_merchant_rules(_user_id: str = Depends(get_current_user_id)):
    return MerchantRulesListResponse(rules=list_global_merchant_rules())


@app.post("/internal/merchant-rules", response_model=InternalMerchantRuleResponse)
async def internal_upsert_merchant_rule(
    request: InternalMerchantRuleRequest,
    x_internal_token: Annotated[str | None, Header()] = None,
):
    expected = os.getenv("CATEGORIZATION_INTERNAL_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Global merchant rules admin is not configured.",
        )
    if not x_internal_token or x_internal_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token.",
        )
    cat = request.category.strip().lower().replace(" ", "_")
    if cat not in _VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown category '{request.category}'.",
        )
    pattern = upsert_global_merchant_rule(request.pattern, cat)
    if pattern is None:
        return InternalMerchantRuleResponse(stored=False, pattern=None)
    return InternalMerchantRuleResponse(stored=True, pattern=pattern)


@app.post("/categorize", response_model=CategorizationResponse)
async def categorize_transaction(
    request: CategorizationRequest,
    user_id: str = Depends(get_current_user_id),
):
    """User-learned rules, global merchant table, UK merchant dictionary, then GPT-4o-mini."""
    category = _resolve_category(user_id, request.description, use_llm=True)
    return CategorizationResponse(category=category)


class BulkCategorizationRequest(BaseModel):
    descriptions: list[str]

class BulkCategorizationResponse(BaseModel):
    results: list[dict]

@app.post("/categorize/bulk", response_model=BulkCategorizationResponse)
async def categorize_bulk(
    request: BulkCategorizationRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Categorize multiple transactions at once"""
    results = []
    for desc in request.descriptions:
        category = _resolve_category(user_id, desc, use_llm=False)
        results.append({"description": desc, "category": category})
    return BulkCategorizationResponse(results=results)


@app.get("/categories")
async def list_categories():
    """List all available categories with merchant examples"""
    return {
        category: {"merchant_count": len(merchants), "examples": merchants[:5]}
        for category, merchants in _CATEGORY_RULES.items()
    }


@app.get("/categories/hmrc-mapping")
async def categories_hmrc_mapping():
    """
    Return all self-employed categories with their HMRC SA103 box references,
    MTD ITSA field names, plain-language descriptions, and guidance warnings.
    Suitable for digital record-keeping export as required by HMRC MTD rules.
    """
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
    try:
        from libs.shared_categories.category_map import export_digital_record_categories
        return {"categories": export_digital_record_categories()}
    except ImportError:
        # Fallback: return basic list from merchant rules
        return {"categories": [{"key": k, "label": k} for k in _CATEGORY_RULES]}
