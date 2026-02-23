import os
import datetime
import json
import redis
from typing import Annotated, List, Optional, Dict, Any
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

app = FastAPI(
    title="Smart Pricing Engine",
    description="Dynamic pricing, usage tracking, and optimization for maximum revenue and retention.",
    version="1.0.0"
)

# --- Security ---
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# --- Redis for real-time usage tracking ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

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

# --- Models ---
class PricingTier(str, Enum):
    FREE = "free"
    STARTER = "starter" 
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

class UsageMetric(str, Enum):
    BANK_CONNECTIONS = "bank_connections"
    TRANSACTIONS_PROCESSED = "transactions_processed"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    TAX_CALCULATIONS = "tax_calculations"
    API_CALLS = "api_calls"
    TEAM_MEMBERS = "team_members"
    ADVANCED_REPORTS = "advanced_reports"

class PricingPlan(BaseModel):
    tier: PricingTier
    name: str
    monthly_price_gbp: float
    annual_price_gbp: float
    annual_discount_percent: int
    limits: Dict[UsageMetric, int]  # -1 means unlimited
    features: List[str]
    target_customer: str
    value_proposition: str

class UserUsage(BaseModel):
    user_id: str
    current_tier: PricingTier
    usage_this_month: Dict[UsageMetric, int]
    usage_limits: Dict[UsageMetric, int]
    overage_charges: float
    subscription_expires: datetime.datetime
    next_billing_date: datetime.datetime

class PricingRecommendation(BaseModel):
    current_tier: PricingTier
    recommended_tier: PricingTier
    reason: str
    potential_savings_monthly: float
    potential_additional_revenue: float
    confidence_score: float  # 0-1

class DynamicPricing(BaseModel):
    base_price: float
    personalized_price: float
    discount_percent: float
    discount_reason: str
    urgency_factor: str
    expires_at: datetime.datetime

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/pricing-plans", response_model=List[PricingPlan])
async def get_pricing_plans():
    """Get all available pricing plans with smart value positioning"""
    
    plants = [
        PricingPlan(
            tier=PricingTier.FREE,
            name="Free",
            monthly_price_gbp=0,
            annual_price_gbp=0,
            annual_discount_percent=0,
            limits={
                UsageMetric.BANK_CONNECTIONS: 1,
                UsageMetric.TRANSACTIONS_PROCESSED: 200,
                UsageMetric.DOCUMENTS_UPLOADED: 10,
                UsageMetric.TAX_CALCULATIONS: 2,
                UsageMetric.API_CALLS: 0,
                UsageMetric.TEAM_MEMBERS: 1
            },
            features=[
                "1 bank connection", 
                "200 transactions/month",
                "Manual categorization",
                "Basic tax calculation",
                "Email support"
            ],
            target_customer="New freelancers testing the waters",
            value_proposition="Get started free, see immediate value"
        ),
        
        PricingPlan(
            tier=PricingTier.STARTER,
            name="Starter",
            monthly_price_gbp=9,
            annual_price_gbp=89,  # 17% discount
            annual_discount_percent=17,
            limits={
                UsageMetric.BANK_CONNECTIONS: 3,
                UsageMetric.TRANSACTIONS_PROCESSED: 1000,
                UsageMetric.DOCUMENTS_UPLOADED: 50,
                UsageMetric.TAX_CALCULATIONS: 12,
                UsageMetric.API_CALLS: 100,
                UsageMetric.TEAM_MEMBERS: 1
            },
            features=[
                "3 bank connections",
                "1,000 transactions/month", 
                "AI categorization",
                "Monthly HMRC submission",
                "Receipt OCR",
                "Cash flow forecasting",
                "Priority support"
            ],
            target_customer="Active freelancers, small side-hustles",
            value_proposition="Save 3+ hours/month, £9 pays for itself in 1 saved hour"
        ),
        
        PricingPlan(
            tier=PricingTier.PRO,
            name="Pro",
            monthly_price_gbp=19,
            annual_price_gbp=189,  # 17% discount  
            annual_discount_percent=17,
            limits={
                UsageMetric.BANK_CONNECTIONS: -1,  # Unlimited
                UsageMetric.TRANSACTIONS_PROCESSED: 5000,
                UsageMetric.DOCUMENTS_UPLOADED: 200,
                UsageMetric.TAX_CALCULATIONS: -1,
                UsageMetric.API_CALLS: 1000,
                UsageMetric.TEAM_MEMBERS: 1,
                UsageMetric.ADVANCED_REPORTS: 10
            },
            features=[
                "Unlimited bank connections",
                "5,000 transactions/month",
                "Advanced ML categorization",
                "Automatic HMRC submission", 
                "Unlimited documents + smart search",
                "Mortgage readiness reports",
                "Advanced analytics & forecasting",
                "API access",
                "Phone support"
            ],
            target_customer="Serious freelancers, consultants earning £3k+/month",
            value_proposition="Complete automation - pay for itself in tax savings alone"
        ),
        
        PricingPlan(
            tier=PricingTier.BUSINESS,
            name="Business",
            monthly_price_gbp=39,
            annual_price_gbp=389,  # 17% discount
            annual_discount_percent=17,
            limits={
                UsageMetric.BANK_CONNECTIONS: -1,
                UsageMetric.TRANSACTIONS_PROCESSED: -1,
                UsageMetric.DOCUMENTS_UPLOADED: -1,
                UsageMetric.TAX_CALCULATIONS: -1,
                UsageMetric.API_CALLS: 10000,
                UsageMetric.TEAM_MEMBERS: 5,
                UsageMetric.ADVANCED_REPORTS: -1
            },
            features=[
                "Everything in Pro",
                "Unlimited everything",
                "Multi-user collaboration",
                "Custom expense policies",
                "Advanced integrations",
                "White-label reports",
                "Dedicated success manager",
                "Custom onboarding"
            ],
            target_customer="Small agencies, teams, high-earning freelancers",
            value_proposition="Scale your business, not your admin overhead"
        ),
        
        PricingPlan(
            tier=PricingTier.ENTERPRISE,
            name="Enterprise",
            monthly_price_gbp=99,
            annual_price_gbp=989,  # 17% discount
            annual_discount_percent=17,
            limits={
                UsageMetric.BANK_CONNECTIONS: -1,
                UsageMetric.TRANSACTIONS_PROCESSED: -1,
                UsageMetric.DOCUMENTS_UPLOADED: -1,
                UsageMetric.TAX_CALCULATIONS: -1,
                UsageMetric.API_CALLS: -1,
                UsageMetric.TEAM_MEMBERS: 50,
                UsageMetric.ADVANCED_REPORTS: -1
            },
            features=[
                "Everything in Business",
                "SSO & advanced security",
                "Custom integrations",
                "Dedicated infrastructure",
                "SLA guarantees", 
                "Legal & compliance consultation",
                "Custom contract terms",
                "24/7 priority support"
            ],
            target_customer="Large agencies, accounting firms, enterprise clients",
            value_proposition="Enterprise-grade solution with guaranteed ROI"
        )
    ]
    
    return plants

@app.get("/usage/{user_id}", response_model=UserUsage)  
async def get_user_usage(
    user_id: str,
    current_user: str = Depends(get_current_user_id)
):
    """Get current usage statistics for user"""
    
    # Get usage from Redis
    usage_key = f"usage:{user_id}:{datetime.datetime.now().strftime('%Y-%m')}"
    usage_data = redis_client.hgetall(usage_key)
    
    # Convert to proper format
    usage_this_month = {}
    for metric in UsageMetric:
        usage_this_month[metric] = int(usage_data.get(metric.value, 0))
    
    # Get user's current plan (mock data for demo)
    current_tier = PricingTier.STARTER
    
    # Get limits for current tier
    plans = await get_pricing_plans()
    current_plan = next(p for p in plans if p.tier == current_tier)
    
    return UserUsage(
        user_id=user_id,
        current_tier=current_tier,
        usage_this_month=usage_this_month,
        usage_limits=current_plan.limits,
        overage_charges=0.0,
        subscription_expires=datetime.datetime.now() + datetime.timedelta(days=15),
        next_billing_date=datetime.datetime.now() + datetime.timedelta(days=15)
    )

@app.post("/track-usage")
async def track_usage_event(
    user_id: str,
    metric: UsageMetric,
    quantity: int = 1,
    current_user: str = Depends(get_current_user_id)
):
    """Track a usage event for billing/limits"""
    
    current_month = datetime.datetime.now().strftime('%Y-%m')
    usage_key = f"usage:{user_id}:{current_month}"
    
    # Increment usage counter
    new_count = redis_client.hincrby(usage_key, metric.value, quantity)
    
    # Set expiry for automatic cleanup
    redis_client.expire(usage_key, 86400 * 40)  # 40 days
    
    # Check if user hit limits and needs upgrade nudge
    user_usage = await get_user_usage(user_id, current_user)
    
    warnings = []
    if user_usage.usage_limits.get(metric, 0) > 0:  # Has a limit
        limit = user_usage.usage_limits[metric]
        if new_count >= limit * 0.8:  # 80% of limit
            warnings.append(f"Approaching {metric.value} limit ({new_count}/{limit})")
        if new_count >= limit:
            warnings.append(f"Exceeded {metric.value} limit! Consider upgrading.")
    
    return {
        "metric": metric.value,
        "new_total": new_count,
        "warnings": warnings,
        "upgrade_suggestion": "Pro plan" if warnings else None
    }

@app.get("/pricing-recommendation/{user_id}", response_model=PricingRecommendation)
async def get_pricing_recommendation(
    user_id: str,
    current_user: str = Depends(get_current_user_id)
):
    """AI-powered pricing recommendation based on usage patterns"""
    
    usage = await get_user_usage(user_id, current_user)
    plans = await get_pricing_plans()
    
    current_plan = next(p for p in plans if p.tier == usage.current_tier)
    
    # Analyze usage patterns
    total_usage_score = 0
    exceeded_limits = []
    
    for metric, count in usage.usage_this_month.items():
        limit = usage.usage_limits.get(metric, -1)
        if limit > 0 and count > limit:
            exceeded_limits.append(metric)
            total_usage_score += 2  # Heavy penalty for exceeded limits
        elif limit > 0 and count > limit * 0.7:
            total_usage_score += 1  # Approaching limit
    
    # Recommendation logic
    if len(exceeded_limits) >= 2:
        # Heavy user, recommend significant upgrade
        recommended_tier = PricingTier.PRO if usage.current_tier == PricingTier.FREE else PricingTier.BUSINESS
        reason = f"You've exceeded limits in {len(exceeded_limits)} areas. Upgrade for unlimited usage."
        potential_additional_revenue = 19.0 if usage.current_tier == PricingTier.FREE else 20.0
        confidence_score = 0.9
    elif len(exceeded_limits) == 1:
        # Moderate upgrade needed
        next_tiers = [PricingTier.STARTER, PricingTier.PRO, PricingTier.BUSINESS, PricingTier.ENTERPRISE]
        current_index = next_tiers.index(usage.current_tier) if usage.current_tier in next_tiers else 0
        recommended_tier = next_tiers[min(current_index + 1, len(next_tiers) - 1)]
        reason = f"You exceeded your {exceeded_limits[0].value} limit. Next tier provides more headroom."
        potential_additional_revenue = 10.0
        confidence_score = 0.7
    elif total_usage_score == 0:
        # Under-utilizing, might downgrade or add value
        if usage.current_tier == PricingTier.PRO:
            recommended_tier = PricingTier.STARTER
            reason = "You're not using Pro features fully. Starter might be more cost-effective."
            potential_additional_revenue = -10.0
            confidence_score = 0.5
        else:
            recommended_tier = usage.current_tier
            reason = "Your current plan fits your usage perfectly."
            potential_additional_revenue = 0.0
            confidence_score = 0.8
    else:
        recommended_tier = usage.current_tier
        reason = "Current plan is optimal for your usage."
        potential_additional_revenue = 0.0
        confidence_score = 0.6
    
    return PricingRecommendation(
        current_tier=usage.current_tier,
        recommended_tier=recommended_tier,
        reason=reason,
        potential_savings_monthly=max(0, -potential_additional_revenue),
        potential_additional_revenue=max(0, potential_additional_revenue),
        confidence_score=confidence_score
    )

@app.get("/dynamic-pricing/{user_id}", response_model=DynamicPricing)
async def get_dynamic_pricing(
    user_id: str,
    target_tier: PricingTier,
    current_user: str = Depends(get_current_user_id)
):
    """Get personalized pricing with smart discounts"""
    
    plans = await get_pricing_plans()
    target_plan = next(p for p in plans if p.tier == target_tier)
    base_price = target_plan.monthly_price_gbp
    
    # Personalization factors
    usage = await get_user_usage(user_id, current_user)
    days_to_billing = (usage.next_billing_date - datetime.datetime.now()).days
    
    discount_percent = 0
    discount_reason = ""
    urgency_factor = ""
    
    # Churn risk discount
    if usage.current_tier == PricingTier.FREE and target_tier == PricingTier.STARTER:
        discount_percent = 25  # First month 25% off
        discount_reason = "New customer welcome offer"
        
    # Urgency discounts
    elif days_to_billing <= 3:
        discount_percent = 15
        discount_reason = "Limited time: upgrade before billing cycle"  
        urgency_factor = "Expires in 3 days"
        
    # Volume discount for high usage
    elif (usage.usage_this_month.get(UsageMetric.TRANSACTIONS_PROCESSED, 0) > 
          usage.usage_limits.get(UsageMetric.TRANSACTIONS_PROCESSED, 0)):
        discount_percent = 20
        discount_reason = "Heavy user discount - thank you for growing with us!"
        
    # Annual plan incentive
    annual_discount = target_plan.annual_discount_percent
    if annual_discount > discount_percent:
        discount_percent = annual_discount
        discount_reason = f"Annual plan - save {annual_discount}% vs monthly billing"
    
    personalized_price = base_price * (1 - discount_percent / 100)
    expires_at = datetime.datetime.now() + datetime.timedelta(days=7)
    
    return DynamicPricing(
        base_price=base_price,
        personalized_price=round(personalized_price, 2),
        discount_percent=discount_percent,
        discount_reason=discount_reason,
        urgency_factor=urgency_factor,
        expires_at=expires_at
    )

@app.get("/pricing-analytics")
async def get_pricing_analytics(
    current_user: str = Depends(get_current_user_id)
):
    """Analytics dashboard for pricing optimization"""
    
    return {
        "conversion_rates": {
            "free_to_starter": 0.23,  # 23% convert within 30 days
            "starter_to_pro": 0.35,   # 35% upgrade within 6 months
            "pro_to_business": 0.18,  # 18% upgrade to business
        },
        "optimal_pricing": {
            "starter_sweet_spot": "£9-12/month",
            "pro_maximum_willingness": "£25/month",
            "enterprise_value_threshold": "£75+/month"
        },
        "revenue_optimization": {
            "current_arpu": 14.50,
            "optimized_arpu_potential": 18.90,
            "improvement_opportunity": "+30.3%",
            "key_levers": [
                "Free trial extension (14 → 30 days): +8% conversion",
                "Usage-based upgrade nudges: +12% Pro upgrades", 
                "Annual billing incentives: +15% revenue per customer",
                "Enterprise pilot program: +£2.5k/month potential"
            ]
        },
        "churn_prevention": {
            "price_sensitive_timeframe": "Days 25-30 of trial",
            "optimal_discount_range": "15-25%",
            "retention_rate_improvement": "+18% with smart pricing"
        }
    }