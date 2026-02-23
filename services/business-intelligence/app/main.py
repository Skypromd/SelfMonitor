import os
from typing import Annotated, List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

app = FastAPI(
    title="Business Intelligence Service", 
    description="Advanced analytics and data monetization platform for comprehensive business insights.",
    version="1.0.0"
)

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

# --- Models ---
class MetricType(str, Enum):
    REVENUE = "revenue"
    ENGAGEMENT = "engagement"
    RETENTION = "retention"
    ACQUISITION = "acquisition"

class DataInsight(BaseModel):
    insight_id: str
    category: str
    title: str
    description: str
    confidence_score: float
    impact_score: float
    actionable_recommendations: List[str]
    created_at: datetime

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/revenue-intelligence")
async def get_revenue_intelligence(
    time_period: str = "last_30_days",
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Comprehensive revenue intelligence and optimization insights"""
    
    return {
        "revenue_overview": {
            "total_revenue": 267000.0,  # £267k current month
            "recurring_revenue": 189450.0,  # £189.45k MRR
            "one_time_revenue": 77550.0,  # £77.55k one-time
            "revenue_growth_rate": 0.34,  # 34% month-over-month growth
            "revenue_per_customer": 187.60,  # £187.60 average per customer
            "customer_lifetime_value": 2340.0  # £2,340 average LTV
        },
        "revenue_streams_analysis": {
            "subscription_revenue": {
                "amount": 189450.0,
                "percentage": 0.71,
                "growth_rate": 0.28
            },
            "enterprise_revenue": {
                "amount": 45600.0,
                "percentage": 0.17,
                "growth_rate": 0.67
            },
            "api_marketplace_revenue": {
                "amount": 18900.0,
                "percentage": 0.07,
                "growth_rate": 1.23
            },
            "premium_features_revenue": {
                "amount": 13050.0,
                "percentage": 0.05,
                "growth_rate": 0.89
            }
        },
        "optimization_opportunities": [
            {
                "opportunity": "Enterprise tier expansion",
                "potential_revenue": 89400.0,
                "implementation_effort": "medium",
                "time_to_impact": "2-3 months"
            },
            {
                "opportunity": "API monetization enhancement", 
                "potential_revenue": 34500.0,
                "implementation_effort": "low",
                "time_to_impact": "3-4 weeks"
            },
            {
                "opportunity": "Premium feature upselling",
                "potential_revenue": 23800.0,
                "implementation_effort": "low",
                "time_to_impact": "2-3 weeks"
            }
        ],
        "predictive_analytics": {
            "next_month_revenue_forecast": 345600.0,  # £345.6k forecast
            "quarter_end_projection": 987500.0,  # £987.5k quarter
            "annual_revenue_trajectory": 3240000.0,  # £3.24M annual
            "confidence_interval": 0.87  # 87% confidence
        },
        "competitive_intelligence": {
            "market_share_estimate": 0.12,  # 12% UK market share
            "pricing_competitiveness": 0.89,  # 89% competitive pricing
            "feature_gap_analysis": ["Advanced ML analytics", "White-label solutions"],
            "competitive_advantages": ["Real-time processing", "Comprehensive automation", "Superior fraud detection"]
        }
    }

@app.get("/customer-intelligence")
async def get_customer_intelligence(
    segment: str = "all",
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Advanced customer behavior analytics and segmentation insights"""
    
    return {
        "customer_segmentation": {
            "high_value_customers": {
                "count": 234,
                "percentage": 0.16,
                "avg_monthly_revenue": 890.0,
                "retention_rate": 0.97,
                "characteristics": ["Enterprise users", "High transaction volume", "Premium features"]
            },
            "growth_customers": {
                "count": 567,
                "percentage": 0.39,
                "avg_monthly_revenue": 245.0,
                "retention_rate": 0.89,
                "characteristics": ["Expanding usage", "Feature adoption", "Engagement growth"]
            },
            "stable_customers": {
                "count": 478, 
                "percentage": 0.33,
                "avg_monthly_revenue": 89.0,
                "retention_rate": 0.84,
                "characteristics": ["Consistent usage", "Basic features", "Price-sensitive"]
            },
            "at_risk_customers": {
                "count": 176,
                "percentage": 0.12,
                "avg_monthly_revenue": 67.0,
                "retention_rate": 0.45,
                "characteristics": ["Declining usage", "Support issues", "Payment problems"]
            }
        },
        "behavior_patterns": {
            "peak_usage_hours": [9, 10, 14, 15, 16],
            "feature_adoption_rates": {
                "basic_features": 0.94,
                "advanced_analytics": 0.67,
                "api_access": 0.34,
                "enterprise_tools": 0.23
            },
            "user_journey_insights": {
                "onboarding_completion": 0.89,
                "time_to_first_value": 2.3,  # 2.3 days
                "feature_discovery_rate": 0.76
            }
        },
        "monetization_insights": {
            "upsell_opportunities": {
                "customers_ready_for_upgrade": 145,
                "estimated_upsell_revenue": 34500.0,
                "success_probability": 0.67
            },
            "cross_sell_potential": {
                "api_marketplace_candidates": 89,
                "enterprise_feature_candidates": 234,
                "premium_support_candidates": 156
            },
            "retention_strategies": [
                "Proactive customer success outreach for at-risk segment",
                "Feature education campaigns for stable customers",
                "Advanced feature trials for growth customers"
            ]
        },
        "predictive_customer_scores": {
            "churn_risk_distribution": {"low": 0.68, "medium": 0.20, "high": 0.08, "critical": 0.04},
            "expansion_potential": {"low": 0.45, "medium": 0.34, "high": 0.21},
            "advocacy_likelihood": {"low": 0.23, "medium": 0.45, "high": 0.32}
        }
    }

@app.get("/market-intelligence")
async def get_market_intelligence(
    region: str = "uk",
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Market trends and competitive intelligence analytics"""
    
    return {
        "market_trends": {
            "fintech_market_growth": 0.23,  # 23% annual growth
            "self_employed_market_size": 4800000,  # 4.8M self-employed in UK
            "digital_adoption_rate": 0.78,  # 78% digital adoption
            "automation_demand": 0.91,  # 91% demand for automation
            "regulatory_technology_growth": 0.34  # 34% RegTech growth
        },
        "competitive_landscape": {
            "total_competitors": 47,
            "direct_competitors": 12,
            "market_leaders": ["FreeAgent", "Xero", "QuickBooks"],
            "competitive_gaps": [
                "Real-time fraud detection",
                "Advanced predictive analytics", 
                "Comprehensive automation",
                "API marketplace ecosystem"
            ]
        },
        "opportunity_analysis": {
            "untapped_market_segments": [
                {
                    "segment": "Creative professionals",
                    "size": 890000,
                    "penetration": 0.12,
                    "revenue_potential": 156000.0
                },
                {
                    "segment": "E-commerce sellers",
                    "size": 567000,
                    "penetration": 0.08,
                    "revenue_potential": 234000.0
                },
                {
                    "segment": "Professional consultants",
                    "size": 1200000,
                    "penetration": 0.15,
                    "revenue_potential": 445000.0
                }
            ],
            "emerging_opportunities": [
                "AI-powered tax optimization",
                "Embedded finance solutions",
                "B2B marketplace integrations",
                "White-label platform offerings"
            ]
        },
        "regulatory_intelligence": {
            "upcoming_regulations": [
                "Enhanced GDPR enforcement",
                "Digital services tax changes",
                "Open banking expansion"
            ],
            "compliance_advantages": [
                "Automated compliance monitoring",
                "Real-time regulatory reporting",
                "Risk-based compliance automation"
            ]
        }
    }

@app.get("/data-monetization-analytics")
async def get_data_monetization_analytics(
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Advanced data monetization strategies and revenue opportunities"""
    
    return {
        "data_assets_valuation": {
            "customer_behavior_data": {
                "estimated_value": 234000.0,  # £234k value
                "monetization_potential": "High",
                "use_cases": ["Predictive analytics services", "Industry benchmarks", "Market research"]
            },
            "transaction_patterns": {
                "estimated_value": 189000.0,
                "monetization_potential": "Medium",
                "use_cases": ["Fraud detection services", "Risk assessment", "Financial insights"]
            },
            "industry_insights": {
                "estimated_value": 156000.0,
                "monetization_potential": "High", 
                "use_cases": ["Market intelligence", "Trend analysis", "Competitive intelligence"]
            }
        },
        "analytics_as_a_service": {
            "target_customers": ["Financial institutions", "Accountancy firms", "Government agencies"],
            "service_offerings": [
                {
                    "service": "Fraud Detection API",
                    "pricing": "£0.05 per transaction",
                    "market_size": 2400000,
                    "revenue_potential": 120000.0
                },
                {
                    "service": "Risk Assessment Platform",
                    "pricing": "£890 per month per client",
                    "market_size": 450,
                    "revenue_potential": 400500.0
                },
                {
                    "service": "Industry Benchmarking",
                    "pricing": "£2,400 per report",
                    "market_size": 180,
                    "revenue_potential": 432000.0
                }
            ]
        },
        "white_label_opportunities": {
            "banking_partnerships": {
                "potential_partners": ["Challenger banks", "Credit unions", "Fintech startups"],
                "revenue_model": "Revenue sharing 15-25%",
                "estimated_annual_revenue": 567000.0
            },
            "software_integrations": {
                "potential_partners": ["ERP systems", "CRM platforms", "Accounting software"],
                "revenue_model": "Per-user licensing £12-45/month",
                "estimated_annual_revenue": 234000.0
            }
        },
        "premium_analytics_features": {
            "advanced_ml_insights": {
                "pricing": "£89 per month",
                "target_adoption": 0.34,
                "estimated_revenue": 67800.0
            },
            "real_time_dashboards": {
                "pricing": "£56 per month",
                "target_adoption": 0.45,
                "estimated_revenue": 89400.0
            },
            "predictive_modeling": {
                "pricing": "£134 per month",
                "target_adoption": 0.23,
                "estimated_revenue": 134500.0
            }
        },
        "total_data_monetization_potential": {
            "direct_analytics_services": 952500.0,
            "white_label_partnerships": 801000.0,
            "premium_feature_upgrades": 291700.0,
            "total_annual_opportunity": 2045200.0,  # £2.045M additional revenue
            "implementation_timeline": "6-12 months",
            "investment_required": 156000.0  # £156k investment
        }
    }

@app.post("/generate-business-insights")
async def generate_business_insights(
    analysis_type: str,
    time_range: str = "last_90_days",
    current_user: str = Depends(get_current_user_id),
    background_tasks: Optional[BackgroundTasks] = None
) -> Dict[str, Any]:
    """AI-powered business insights generation and recommendations"""
    
    # Define insight generation algorithms
    insight_generators: Dict[str, Dict[str, Any]] = {
        "revenue_optimization": {
            "data_sources": ["revenue_streams", "customer_segments", "pricing_data"],
            "ml_models": ["revenue_forecasting", "price_optimization", "customer_value"],
            "impact_score": 0.89
        },
        "customer_experience": {
            "data_sources": ["user_behavior", "support_tickets", "feature_usage"],
            "ml_models": ["sentiment_analysis", "journey_optimization", "satisfaction_prediction"],
            "impact_score": 0.76
        },
        "operational_efficiency": {
            "data_sources": ["process_metrics", "cost_data", "automation_stats"],
            "ml_models": ["process_optimization", "cost_prediction", "efficiency_scoring"],
            "impact_score": 0.82
        }
    }
    
    generator: Dict[str, Any] = insight_generators.get(analysis_type, insight_generators["revenue_optimization"])
    
    # Mock AI-generated insights
    insights: List[Dict[str, Any]] = [
        {
            "insight_id": f"BI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": "Enterprise segment expansion opportunity",
            "confidence_score": 0.91,
            "impact_score": 0.89,
            "description": "Analysis shows 34% of Professional tier customers exhibit enterprise-level usage patterns",
            "recommendations": [
                "Create targeted enterprise upgrade campaigns",
                "Develop enterprise-specific feature bundles",
                "Implement white-glove onboarding for enterprise prospects"
            ],
            "estimated_revenue_impact": 156000.0
        },
        {
            "insight_id": f"BI-{datetime.now().strftime('%Y%m%d%H%M%S')}-2",
            "title": "API marketplace untapped potential",
            "confidence_score": 0.87,
            "impact_score": 0.76,
            "description": "67% of high-value customers are not using API features despite significant integration opportunities",
            "recommendations": [
                "Launch API education campaign",
                "Offer free API trial credits",
                "Develop integration partnerships with popular business tools"
            ],
            "estimated_revenue_impact": 67800.0
        }
    ]
    
    # Schedule background insight processing
    if background_tasks is not None:
        background_tasks.add_task(process_advanced_insights, analysis_type, generator)
    
    return {
        "analysis_type": analysis_type,
        "time_range": time_range,
        "insights_generated": len(insights),
        "insights": insights,
        "total_potential_impact": sum(float(insight["estimated_revenue_impact"]) for insight in insights),
        "confidence_score": sum(float(insight["confidence_score"]) for insight in insights) / len(insights),
        "processing_status": "Insights generated - advanced analysis in progress"
    }

async def process_advanced_insights(analysis_type: str, generator: Dict[str, Any]):
    """Process advanced AI insights in background"""
    print(f"🧠 Processing advanced insights for {analysis_type}")
    print(f"📊 ML Models: {generator['ml_models']}")
    print(f"📈 Impact Score: {generator['impact_score']}")
    print("✅ Advanced insights processing completed")

@app.get("/executive-dashboard")
async def get_executive_dashboard(
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Executive-level business intelligence dashboard with KPIs and strategic insights"""
    
    return {
        "key_performance_indicators": {
            "monthly_recurring_revenue": 189450.0,
            "customer_acquisition_cost": 45.60,
            "customer_lifetime_value": 2340.0,
            "churn_rate": 0.06,  # 6% monthly churn
            "net_revenue_retention": 1.23,  # 123% NRR
            "gross_margin": 0.84  # 84% gross margin
        },
        "growth_metrics": {
            "revenue_growth_rate": 0.34,  # 34% month-over-month
            "customer_growth_rate": 0.28,  # 28% customer growth
            "market_expansion": 0.23,  # 23% market expansion
            "product_adoption": 0.67  # 67% feature adoption rate
        },
        "strategic_opportunities": [
            {
                "opportunity": "International expansion",
                "market_potential": 4500000.0,
                "implementation_complexity": "high",
                "time_horizon": "12-18 months",
                "roi_projection": 5.6
            },
            {
                "opportunity": "Enterprise platform development",
                "market_potential": 1200000.0,
                "implementation_complexity": "medium",
                "time_horizon": "6-9 months",
                "roi_projection": 3.4
            },
            {
                "opportunity": "Data monetization services",
                "market_potential": 2045200.0,
                "implementation_complexity": "medium",
                "time_horizon": "9-12 months",
                "roi_projection": 13.1
            }
        ],
        "competitive_positioning": {
            "market_share": 0.12,  # 12% UK market share
            "competitive_advantages": ["Advanced automation", "Superior fraud detection", "Real-time analytics"],
            "threat_assessment": "Low - strong technological moat",
            "innovation_index": 0.89  # 89% innovation score vs competitors
        },
        "financial_health": {
            "cash_runway": "18+ months",
            "burn_rate": -12400.0,  # Negative burn rate = profitability
            "profitability_margin": 0.34,  # 34% profit margin
            "debt_to_equity": 0.0,  # Zero debt
            "working_capital": 456000.0  # £456k working capital
        }
    }