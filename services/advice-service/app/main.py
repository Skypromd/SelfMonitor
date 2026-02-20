import datetime
import os
from collections import defaultdict
from typing import Annotated, Literal, Optional

import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

# --- Configuration ---
TRANSACTIONS_SERVICE_URL = os.getenv("TRANSACTIONS_SERVICE_URL", "http://localhost:8002/transactions/me")

# --- Security ---
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    credentials_exception = HTTPException(
        status_code=401,
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
    title="Advice Service",
    description="Provides non-regulated financial insights.",
    version="1.0.0"
)

# --- Models ---
class Transaction(BaseModel):
    date: datetime.date
    amount: float
    description: str
    category: Optional[str] = None # Добавлено для полного соответствия

class AdviceRequest(BaseModel):
    topic: Literal['spending_analysis', 'savings_potential', 'income_protection']

class AdviceResponse(BaseModel):
    topic: Literal['spending_analysis', 'savings_potential', 'income_protection']
    headline: str
    details: str
    generated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))

# --- Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/generate", response_model=AdviceResponse)
async def generate_advice(
    request: AdviceRequest, 
    user_id: str = Depends(get_current_user_id),
    auth_token: str = Depends(oauth2_scheme),
):
    print(f"Generating advice for user {user_id} on topic: {request.topic}")

    # --- Fetch transactions once for all topics that need them ---
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = await client.get(TRANSACTIONS_SERVICE_URL, headers=headers, timeout=10.0)
            response.raise_for_status()
            transactions = [Transaction(**t) for t in response.json()]
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to transactions-service: {e}")

    # --- Topic-specific logic ---
    if request.topic == 'income_protection':
        # 1. Calculate average monthly income over last year
        twelve_months_ago = datetime.date.today() - datetime.timedelta(days=365)
        monthly_income = defaultdict(float)
        for t in transactions:
            if t.date >= twelve_months_ago and t.amount > 0:
                monthly_income[t.date.strftime("%Y-%m")] += t.amount

        if not monthly_income:
            return AdviceResponse(
                topic='income_protection',
                headline="Not enough data for an income protection analysis.",
                details="We need more historical income data to provide a recommendation."
            )

        average_monthly_income = sum(monthly_income.values()) / len(monthly_income)

        # New, more persuasive text based on the "Problem -> Solution" formula
        headline = f"Your average income is £{average_monthly_income:,.0f}/month. What if it suddenly stopped?"
        details = (
            "As a self-employed professional, you don't have paid sick leave. "
            "This means any illness or injury preventing you from working can directly impact your financial stability. "
            "Income protection is your safety net, replacing a significant portion of your income so you can focus on recovery, not bills."
        )

        return AdviceResponse(
            topic='income_protection',
            headline=headline,
            details=details
        )

    if request.topic == 'spending_analysis':
        today = datetime.date.today()
        six_months_ago = today - datetime.timedelta(days=180)

        monthly_spending = defaultdict(float)
        for t in transactions:
            if t.date >= six_months_ago and t.amount < 0:
                monthly_spending[t.date.strftime("%Y-%m")] += abs(t.amount)

        if len(monthly_spending) < 2:
            return AdviceResponse(topic='spending_analysis', headline="Not enough data for spending analysis.", details="We need at least two months of spending data to compare.")

        current_month_str = today.strftime("%Y-%m")
        current_month_spending = monthly_spending.pop(current_month_str, 0)

        if not monthly_spending:
             return AdviceResponse(topic='spending_analysis', headline="This is your first month!", details=f"You've spent £{current_month_spending:,.2f} so far. We'll have more insights for you next month.")

        avg_previous_spending = sum(monthly_spending.values()) / len(monthly_spending)

        if current_month_spending > avg_previous_spending * 1.2: # 20% higher
            headline = f"Your spending is up by {((current_month_spending/avg_previous_spending)-1):.0%} this month."
            details = f"You've spent £{current_month_spending:,.2f} so far this month, compared to a recent average of £{avg_previous_spending:,.2f}. It might be a good idea to review your recent activity."
        else:
            headline = "Your spending is on track this month."
            details = f"You've spent £{current_month_spending:,.2f}, which is in line with your average of £{avg_previous_spending:,.2f}. Keep up the good work!"

        return AdviceResponse(topic='spending_analysis', headline=headline, details=details)

    if request.topic == 'savings_potential':
        subscription_keywords = ['netflix', 'spotify', 'amazon prime', 'disney+', 'nowtv', 'audible']
        found_subscriptions = defaultdict(float)

        ninety_days_ago = datetime.date.today() - datetime.timedelta(days=90)

        for t in transactions:
            if t.date >= ninety_days_ago and t.amount < 0:
                for keyword in subscription_keywords:
                    if keyword in t.description.lower():
                        # Use description as a key to avoid double counting
                        found_subscriptions[t.description.lower()] = abs(t.amount)
                        break

        if not found_subscriptions:
            return AdviceResponse(topic='savings_potential', headline="No recurring subscriptions found.", details="We couldn't identify any common subscriptions in your recent transactions.")

        total_monthly_cost = sum(found_subscriptions.values())
        headline = f"You could save £{total_monthly_cost:,.2f} per month on subscriptions."
        details = f"We found {len(found_subscriptions)} potential recurring subscriptions, including '{list(found_subscriptions.keys())[0]}'. Are you still using all of them?"

        return AdviceResponse(topic='savings_potential', headline=headline, details=details)

    raise HTTPException(status_code=400, detail="Invalid topic")
