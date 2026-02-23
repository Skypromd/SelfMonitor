"""
SelfMonitor B2B Sales Automation & Enterprise Customer Acquisition Module
Advanced enterprise sales automation for accelerated B2B growth and strategic partnerships

Features:
- Enterprise customer profiling and lead scoring
- Automated sales funnel management
- Account-based marketing (ABM) campaigns
- Enterprise proposal and contract automation
- Strategic account management
- Sales performance analytics and forecasting
- Customer success and expansion tracking
- Integration with CRM and marketing automation
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Literal
from enum import Enum
import uuid

from pydantic import BaseModel, Field

# --- Business Models ---

class LeadSource(str, Enum):
    """Enterprise lead acquisition sources"""
    PARTNER_REFERRAL = "partner_referral"
    INBOUND_MARKETING = "inbound_marketing"
    OUTBOUND_SALES = "outbound_sales"
    TRADE_SHOWS = "trade_shows"
    WEBINARS = "webinars"
    CONTENT_MARKETING = "content_marketing"
    SOCIAL_SELLING = "social_selling"
    COLD_OUTREACH = "cold_outreach"
    EXISTING_CUSTOMER = "existing_customer"
    STRATEGIC_ALLIANCE = "strategic_alliance"

class CompanySize(str, Enum):
    """Enterprise company size classification"""
    STARTUP = "startup"              # 1-50 employees
    SMB = "smb"                     # 51-200 employees  
    MID_MARKET = "mid_market"       # 201-1000 employees
    ENTERPRISE = "enterprise"       # 1001-5000 employees
    LARGE_ENTERPRISE = "large_enterprise"  # 5000+ employees

class Industry(str, Enum):
    """Target industry verticals"""
    FINANCIAL_SERVICES = "financial_services"
    BANKING = "banking"
    INSURANCE = "insurance"
    FINTECH = "fintech"
    ACCOUNTING = "accounting"
    CONSULTING = "consulting"
    REAL_ESTATE = "real_estate"
    HEALTHCARE = "healthcare"
    TECHNOLOGY = "technology"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    GOVERNMENT = "government"

class SalesStage(str, Enum):
    """B2B sales pipeline stages"""
    LEAD = "lead"                   # Initial lead qualification
    QUALIFIED = "qualified"         # Marketing qualified lead (MQL)
    OPPORTUNITY = "opportunity"     # Sales qualified lead (SQL)
    PROPOSAL = "proposal"           # Proposal presentation stage
    NEGOTIATION = "negotiation"     # Contract negotiation
    CLOSED_WON = "closed_won"      # Deal won
    CLOSED_LOST = "closed_lost"    # Deal lost
    NURTURING = "nurturing"        # Long-term nurturing

class DealComplexity(str, Enum):
    """Deal complexity classification"""
    SIMPLE = "simple"               # Standard pricing, quick decision
    MODERATE = "moderate"           # Some customization, multiple stakeholders  
    COMPLEX = "complex"             # High customization, long sales cycle
    STRATEGIC = "strategic"         # Strategic transformation, C-level involvement

class DecisionMakerRole(str, Enum):
    """Enterprise decision maker roles"""
    CEO = "ceo"
    CFO = "cfo"
    CTO = "cto"
    VP_FINANCE = "vp_finance"
    VP_TECHNOLOGY = "vp_technology"
    DIRECTOR_FINANCE = "director_finance"
    FINANCE_MANAGER = "finance_manager"
    IT_DIRECTOR = "it_director"
    PROCUREMENT = "procurement"
    BUSINESS_ANALYST = "business_analyst"

class EnterpriseAccount(BaseModel):
    """Enterprise customer account profile"""
    account_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    domain: str
    industry: Industry
    company_size: CompanySize
    annual_revenue: Optional[Decimal] = None
    employee_count: Optional[int] = None
    headquarters_location: str
    
    # Technology profile
    current_tech_stack: List[str] = []
    integration_requirements: List[str] = []
    compliance_requirements: List[str] = []
    
    # Financial profile
    financial_complexity: DealComplexity = DealComplexity.MODERATE
    budget_range_min: Optional[Decimal] = None
    budget_range_max: Optional[Decimal] = None
    budget_cycle: Optional[str] = None  # "annual", "quarterly", etc.
    
    # Relationship tracking
    primary_contact: Optional[str] = None
    decision_makers: List[Dict[str, str]] = []
    champion_contact: Optional[str] = None
    
    # Account intelligence
    pain_points: List[str] = []
    strategic_initiatives: List[str] = []
    competitive_landscape: List[str] = []
    expansion_opportunities: List[str] = []
    
    # Timing and readiness
    purchase_timeline: Optional[str] = None
    decision_urgency: Literal["low", "medium", "high", "urgent"] = "medium"
    budget_approved: bool = False
    procurement_process: Optional[str] = None
    
    # Account value and scoring
    account_score: float = Field(ge=0.0, le=100.0, default=50.0)
    lifetime_value_estimate: Optional[Decimal] = None
    expansion_potential: Optional[Decimal] = None
    
    # Relationship status
    account_status: Literal["prospect", "active", "at_risk", "churned", "expansion"] = "prospect"
    customer_health_score: Optional[float] = Field(ge=0.0, le=100.0, default=None)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SalesOpportunity(BaseModel):
    """Enterprise sales opportunity tracking"""
    opportunity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_id: str
    opportunity_name: str
    description: Optional[str] = None
    
    # Deal details
    deal_value: Decimal = Field(ge=0)
    currency: str = "GBP"
    deal_complexity: DealComplexity
    sales_stage: SalesStage = SalesStage.LEAD
    
    # Stakeholders and influence
    primary_contact: str
    decision_makers: List[Dict[str, Any]] = []
    influencers: List[Dict[str, Any]] = []
    champions: List[str] = []
    blockers: List[str] = []
    
    # Timeline and probability
    estimated_close_date: datetime
    probability: float = Field(ge=0.0, le=1.0)
    days_in_stage: int = 0
    sales_cycle_length: Optional[int] = None
    
    # Competition and positioning
    competitors: List[str] = []
    our_competitive_advantage: List[str] = []
    key_differentiators: List[str] = []
    
    # Requirements and solution
    customer_requirements: List[str] = []
    proposed_solution: Optional[str] = None
    implementation_timeline: Optional[str] = None
    support_requirements: List[str] = []
    
    # Commercial terms
    pricing_model: str = "subscription"
    contract_length_months: int = 12
    payment_terms: str = "monthly"
    discount_applied: Decimal = Field(ge=0.0, le=1.0, default=Decimal("0"))
    
    # Sales team
    account_executive: str
    sales_engineer: Optional[str] = None
    customer_success_manager: Optional[str] = None
    
    # Next steps and activities
    next_steps: List[str] = []
    last_activity_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_activity_date: Optional[datetime] = None
    
    # Lead source and attribution
    lead_source: LeadSource
    lead_source_detail: Optional[str] = None
    partner_attribution: Optional[str] = None
    campaign_attribution: Optional[str] = None
    
    # Tracking
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SalesActivity(BaseModel):
    """Sales activity and touchpoint tracking"""
    activity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    opportunity_id: str
    account_id: str
    
    # Activity details
    activity_type: Literal["call", "email", "meeting", "demo", "proposal", "contract", "follow_up"] = "call"
    subject: str
    description: Optional[str] = None
    
    # Participants
    sales_rep: str
    customer_participants: List[str] = []
    internal_participants: List[str] = []
    
    # Outcome and next steps
    outcome: Optional[str] = None
    next_steps: List[str] = []
    follow_up_date: Optional[datetime] = None
    
    # Content and materials
    materials_shared: List[str] = []
    customer_feedback: Optional[str] = None
    objections_raised: List[str] = []
    
    # Activity tracking
    duration_minutes: Optional[int] = None
    activity_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProposalTemplate(BaseModel):
    """Enterprise proposal template and automation"""
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_name: str
    description: str
    
    # Template categorization
    industry: Industry
    company_size: CompanySize
    deal_complexity: DealComplexity
    use_case: str
    
    # Proposal structure
    executive_summary: str
    business_case: str
    solution_overview: str
    technical_requirements: List[str] = []
    implementation_plan: str
    pricing_structure: Dict[str, Any] = {}
    terms_and_conditions: str
    
    # Customization points
    variable_fields: List[str] = []
    conditional_sections: List[Dict[str, Any]] = []
    
    # Performance tracking
    usage_count: int = 0
    win_rate: float = 0.0
    average_deal_size: Optional[Decimal] = None
    
    # Template management
    is_active: bool = True
    version: str = "1.0"
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- Service Classes ---

class EnterpriseLeadScoringService:
    """AI-powered enterprise lead scoring and qualification"""
    
    def __init__(self):
        self.scoring_weights = {
            "company_size": 0.25,
            "industry_fit": 0.20,
            "budget_qualification": 0.20,
            "decision_maker_access": 0.15,
            "timing_urgency": 0.10,
            "competitive_position": 0.10
        }
    
    def calculate_lead_score(self, account: EnterpriseAccount, opportunity: SalesOpportunity) -> float:
        """Comprehensive enterprise lead scoring algorithm"""
        
        score = 0.0
        
        # Company size scoring
        size_scores = {
            CompanySize.LARGE_ENTERPRISE: 25.0,
            CompanySize.ENTERPRISE: 20.0,
            CompanySize.MID_MARKET: 15.0,
            CompanySize.SMB: 10.0,
            CompanySize.STARTUP: 5.0
        }
        score += size_scores.get(account.company_size, 0) * self.scoring_weights["company_size"]
        
        # Industry fit scoring
        if account.industry in [Industry.FINANCIAL_SERVICES, Industry.BANKING, Industry.FINTECH]:
            industry_score = 20.0  # Perfect fit
        elif account.industry in [Industry.INSURANCE, Industry.ACCOUNTING]:
            industry_score = 15.0  # Good fit
        else:
            industry_score = 10.0  # Moderate fit
        score += industry_score * self.scoring_weights["industry_fit"]
        
        # Budget qualification scoring
        if opportunity.deal_value >= 100000:
            budget_score = 20.0
        elif opportunity.deal_value >= 50000:
            budget_score = 15.0
        elif opportunity.deal_value >= 25000:
            budget_score = 10.0
        else:
            budget_score = 5.0
        score += budget_score * self.scoring_weights["budget_qualification"]
        
        # Decision maker access
        decision_maker_score = min(len(opportunity.decision_makers) * 5.0, 15.0)
        score += decision_maker_score * self.scoring_weights["decision_maker_access"]
        
        # Timing and urgency
        urgency_scores = {"urgent": 10.0, "high": 8.0, "medium": 5.0, "low": 2.0}
        urgency_score = urgency_scores.get(account.decision_urgency, 0)
        score += urgency_score * self.scoring_weights["timing_urgency"]
        
        # Competitive position
        competitive_score = 10.0 if len(opportunity.competitors) <= 2 else 5.0
        score += competitive_score * self.scoring_weights["competitive_position"]
        
        return min(score, 100.0)
    
    def get_lead_qualification_recommendations(self, account: EnterpriseAccount) -> List[str]:
        """Get AI-powered lead qualification recommendations"""
        recommendations = []  # type: ignore
        
        if not account.primary_contact:
            recommendations.append("Identify and establish primary contact relationship")  # type: ignore
        
        if not account.decision_makers:
            recommendations.append("Map enterprise decision-making process and stakeholders")  # type: ignore
        
        if not account.budget_range_min:
            recommendations.append("Qualify budget range and procurement process")  # type: ignore
        
        if not account.pain_points:
            recommendations.append("Conduct discovery to identify key business pain points")  # type: ignore
        
        if account.company_size == CompanySize.LARGE_ENTERPRISE and not account.compliance_requirements:
            recommendations.append("Assess enterprise security and compliance requirements")  # type: ignore
        
        if not account.current_tech_stack:
            recommendations.append("Understand current technology landscape and integrations")  # type: ignore
        
        return recommendations  # type: ignore

class SalesForecastingService:
    """Advanced sales forecasting and pipeline analytics"""
    
    def __init__(self):
        self.stage_probabilities = {
            SalesStage.LEAD: 0.05,
            SalesStage.QUALIFIED: 0.15,
            SalesStage.OPPORTUNITY: 0.25,
            SalesStage.PROPOSAL: 0.50,
            SalesStage.NEGOTIATION: 0.75,
            SalesStage.CLOSED_WON: 1.0,
            SalesStage.CLOSED_LOST: 0.0,
            SalesStage.NURTURING: 0.10
        }
    
    def generate_sales_forecast(self, opportunities: List[SalesOpportunity]) -> Dict[str, Any]:
        """Generate comprehensive sales forecast"""
        
        pipeline_value = sum(opp.deal_value for opp in opportunities if opp.sales_stage != SalesStage.CLOSED_LOST)
        weighted_pipeline = sum(opp.deal_value * Decimal(str(opp.probability)) for opp in opportunities)  # type: ignore
        
        # Forecast by time period
        current_quarter_deals = self._filter_by_quarter(opportunities, 0)
        next_quarter_deals = self._filter_by_quarter(opportunities, 1)
        
        current_quarter_forecast = sum(
            opp.deal_value * Decimal(str(opp.probability))  # type: ignore
            for opp in current_quarter_deals 
            if opp.sales_stage not in [SalesStage.CLOSED_LOST, SalesStage.CLOSED_WON]
        )
        
        next_quarter_forecast = sum(
            opp.deal_value * Decimal(str(opp.probability))  # type: ignore
            for opp in next_quarter_deals 
            if opp.sales_stage not in [SalesStage.CLOSED_LOST, SalesStage.CLOSED_WON]
        )
        
        # Win rate analysis
        closed_deals = [opp for opp in opportunities if opp.sales_stage in [SalesStage.CLOSED_WON, SalesStage.CLOSED_LOST]]
        won_deals = [opp for opp in closed_deals if opp.sales_stage == SalesStage.CLOSED_WON]
        win_rate = len(won_deals) / len(closed_deals) if closed_deals else 0
        
        return {
            "pipeline_summary": {
                "total_opportunities": len(opportunities),
                "total_pipeline_value": float(pipeline_value),
                "weighted_pipeline_value": float(weighted_pipeline),
                "average_deal_size": float(pipeline_value / len(opportunities)) if opportunities else 0
            },
            "quarterly_forecast": {
                "current_quarter": {
                    "deals_count": len(current_quarter_deals),
                    "forecast_value": float(current_quarter_forecast),
                    "best_case_value": float(sum(opp.deal_value for opp in current_quarter_deals))
                },
                "next_quarter": {
                    "deals_count": len(next_quarter_deals),
                    "forecast_value": float(next_quarter_forecast),
                    "best_case_value": float(sum(opp.deal_value for opp in next_quarter_deals))
                }
            },
            "performance_metrics": {
                "overall_win_rate": win_rate,
                "average_sales_cycle_days": self._calculate_avg_sales_cycle(opportunities),
                "pipeline_velocity": self._calculate_pipeline_velocity(opportunities)
            },
            "pipeline_by_stage": self._analyze_pipeline_by_stage(opportunities),
            "forecast_accuracy": self._calculate_forecast_accuracy(opportunities)
        }
    
    def _filter_by_quarter(self, opportunities: List[SalesOpportunity], quarter_offset: int) -> List[SalesOpportunity]:
        """Filter opportunities by quarter"""
        today = datetime.now(timezone.utc)
        target_quarter_start = today + timedelta(days=quarter_offset * 90)
        target_quarter_end = target_quarter_start + timedelta(days=90)
        
        return [
            opp for opp in opportunities
            if target_quarter_start <= opp.estimated_close_date <= target_quarter_end
        ]
    
    def _calculate_avg_sales_cycle(self, opportunities: List[SalesOpportunity]) -> float:
        """Calculate average sales cycle length"""
        cycles = [opp.sales_cycle_length for opp in opportunities if opp.sales_cycle_length]
        return sum(cycles) / len(cycles) if cycles else 0.0
    
    def _calculate_pipeline_velocity(self, opportunities: List[SalesOpportunity]) -> float:
        """Calculate pipeline velocity metric"""
        # Simplified velocity calculation: deal value / days in current stage
        velocities = []
        for opp in opportunities:
            if opp.days_in_stage > 0:
                velocity = float(opp.deal_value) / opp.days_in_stage
                velocities.append(velocity)  # type: ignore
        return sum(velocities) / len(velocities) if velocities else 0.0  # type: ignore
    
    def _analyze_pipeline_by_stage(self, opportunities: List[SalesOpportunity]) -> Dict[str, Any]:
        """Analyze pipeline distribution by sales stage"""
        stage_analysis = {}
        
        for stage in SalesStage:
            stage_opps = [opp for opp in opportunities if opp.sales_stage == stage]
            stage_analysis[stage.value] = {
                "count": len(stage_opps),
                "total_value": float(sum(opp.deal_value for opp in stage_opps)),
                "average_deal_size": float(sum(opp.deal_value for opp in stage_opps) / len(stage_opps)) if stage_opps else 0,
                "weighted_value": float(sum(opp.deal_value * Decimal(str(opp.probability)) for opp in stage_opps))  # type: ignore
            }
        
        return stage_analysis  # type: ignore
    
    def _calculate_forecast_accuracy(self, opportunities: List[SalesOpportunity]) -> Dict[str, float]:
        """Calculate historical forecast accuracy"""
        # Mock accuracy metrics - in production: compare historical forecasts vs actual results
        return {
            "current_quarter_accuracy": 0.87,  # 87% accuracy
            "previous_quarter_accuracy": 0.82,
            "trailing_12_month_accuracy": 0.85,
            "forecast_bias": 0.05  # 5% optimistic bias
        }

class AccountBasedMarketingService:
    """Account-based marketing automation for enterprise accounts"""
    
    def __init__(self):
        self.campaign_templates = {}
    
    def create_abm_campaign(self, target_accounts: List[EnterpriseAccount]) -> Dict[str, Any]:
        """Create personalized ABM campaign for target enterprise accounts"""
        
        campaign_id = str(uuid.uuid4())
        
        # Segment accounts by characteristics
        segments = self._segment_accounts(target_accounts)
        
        # Generate personalized content strategy
        content_strategy = self._generate_content_strategy(segments)
        
        # Create multi-channel engagement plan
        engagement_plan = self._create_engagement_plan(target_accounts)
        
        return {
            "campaign_id": campaign_id,
            "campaign_name": f"Enterprise ABM Campaign {datetime.now(timezone.utc).strftime('%Y-%m')}",
            "target_accounts_count": len(target_accounts),
            "account_segments": segments,
            "content_strategy": content_strategy,
            "engagement_plan": engagement_plan,
            "success_metrics": {
                "target_engagement_rate": 0.15,  # 15% engagement
                "target_meeting_conversion": 0.08,  # 8% meeting conversion
                "target_pipeline_generation": 500000,  # £500K pipeline
                "campaign_duration_weeks": 8
            },
            "budget_allocation": {
                "content_creation": 15000,
                "paid_advertising": 25000,
                "events_webinars": 20000,
                "sales_enablement": 10000,
                "total_budget": 70000
            }
        }
    
    def _segment_accounts(self, accounts: List[EnterpriseAccount]) -> Dict[str, List[str]]:
        """Segment accounts by key characteristics"""
        
        segments = {  # type: ignore
            "enterprise_banking": [],
            "fintech_growth": [],
            "insurance_digital": [],
            "mid_market_finance": [],
            "government_public": []
        }
        
        for account in accounts:
            if account.industry == Industry.BANKING and account.company_size in [CompanySize.ENTERPRISE, CompanySize.LARGE_ENTERPRISE]:
                segments["enterprise_banking"].append(account.account_id)  # type: ignore
            elif account.industry == Industry.FINTECH:
                segments["fintech_growth"].append(account.account_id)  # type: ignore
            elif account.industry == Industry.INSURANCE:
                segments["insurance_digital"].append(account.account_id)  # type: ignore
            elif account.company_size == CompanySize.MID_MARKET:
                segments["mid_market_finance"].append(account.account_id)  # type: ignore
            elif account.industry == Industry.GOVERNMENT:
                segments["government_public"].append(account.account_id)  # type: ignore
        
        return {k: v for k, v in segments.items() if v}  # Remove empty segments
    
    def _generate_content_strategy(self, segments: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate personalized content strategy for each segment"""
        
        content_map = {
            "enterprise_banking": {
                "content_themes": ["Digital transformation", "Regulatory compliance", "Customer experience"],
                "content_formats": ["Executive briefings", "ROI calculators", "Compliance guides"],
                "key_messaging": ["Enterprise-grade security", "Scalable architecture", "Regulatory expertise"]
            },
            "fintech_growth": {
                "content_themes": ["Scaling operations", "API integration", "Market expansion"],
                "content_formats": ["Technical whitepapers", "Implementation guides", "Success stories"],
                "key_messaging": ["Developer-friendly APIs", "Rapid integration", "Scalable pricing"]
            },
            "insurance_digital": {
                "content_themes": ["Digital claims processing", "Risk assessment", "Customer onboarding"],
                "content_formats": ["Process automation guides", "Risk management studies", "Digital transformation roadmaps"],
                "key_messaging": ["Automated workflows", "Advanced analytics", "Digital-first approach"]
            }
        }
        
        return {segment: content_map.get(segment, {}) for segment in segments.keys()}
    
    def _create_engagement_plan(self, accounts: List[EnterpriseAccount]) -> Dict[str, Any]:
        """Create multi-channel engagement plan"""
        
        return {
            "engagement_channels": {
                "linkedin_outreach": {
                    "target_roles": ["CFO", "VP Finance", "Finance Director"],
                    "message_sequence": 4,
                    "expected_response_rate": 0.12
                },
                "email_nurturing": {
                    "email_sequence": 6,
                    "personalization_level": "Account-specific",
                    "expected_open_rate": 0.25
                },
                "content_syndication": {
                    "platforms": ["Finance publications", "Industry forums", "Trade publications"],
                    "content_pieces": 8,
                    "expected_engagement": 0.08
                },
                "webinar_series": {
                    "webinar_count": 3,
                    "topics": ["Financial automation", "Compliance best practices", "ROI optimization"],
                    "expected_attendance": 45
                }
            },
            "touchpoint_sequence": [
                {"week": 1, "activity": "LinkedIn connection + content share"},
                {"week": 2, "activity": "Personalized email with industry insight"},
                {"week": 3, "activity": "Webinar invitation"},
                {"week": 4, "activity": "Case study delivery"},
                {"week": 6, "activity": "Demo offer with ROI calculator"},
                {"week": 8, "activity": "Executive briefing proposal"}
            ]
        }

# Initialize services
lead_scoring = EnterpriseLeadScoringService()
forecasting = SalesForecastingService()
abm_service = AccountBasedMarketingService()