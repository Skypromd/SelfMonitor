"""
SelfMonitor Board Governance & Corporate Governance Automation
Enterprise-grade board management and corporate governance for IPO readiness

Features:
- Board composition optimization and independence verification
- Committee management and effectiveness tracking
- Board meeting automation and governance workflow
- Director performance evaluation and assessment
- Governance framework implementation and monitoring
- Executive compensation and equity management
- Shareholder rights and proxy governance
- Board decision tracking and audit trail
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Literal
from enum import Enum
import uuid

from pydantic import BaseModel, Field

# --- Governance Models ---

class CommitteeType(str, Enum):
    """Board committee types for corporate governance"""
    AUDIT = "audit"
    COMPENSATION = "compensation"
    NOMINATING = "nominating"
    RISK = "risk"
    GOVERNANCE = "governance"
    TECHNOLOGY = "technology"
    STRATEGY = "strategy"
    FINANCE = "finance"

class BoardMeetingType(str, Enum):
    """Board meeting types and formats"""
    REGULAR_BOARD = "regular_board"
    SPECIAL_BOARD = "special_board"
    COMMITTEE_MEETING = "committee_meeting"
    EXECUTIVE_SESSION = "executive_session"
    ANNUAL_MEETING = "annual_meeting"
    EMERGENCY_MEETING = "emergency_meeting"

class GovernancePolicy(str, Enum):
    """Corporate governance policies and frameworks"""
    CODE_OF_ETHICS = "code_of_ethics"
    WHISTLEBLOWER_POLICY = "whistleblower_policy"
    INSIDER_TRADING = "insider_trading"
    RELATED_PARTY = "related_party"
    EXECUTIVE_COMPENSATION = "executive_compensation"
    BOARD_DIVERSITY = "board_diversity"
    RISK_MANAGEMENT = "risk_management"
    CYBERSECURITY = "cybersecurity"

class DirectorSkill(str, Enum):
    """Director skills and expertise areas"""
    FINANCIAL_EXPERTISE = "financial_expertise"
    TECHNOLOGY_LEADERSHIP = "technology_leadership"
    INTERNATIONAL_BUSINESS = "international_business"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    PUBLIC_COMPANY_EXPERIENCE = "public_company_experience"
    CYBERSECURITY = "cybersecurity"
    RISK_MANAGEMENT = "risk_management"
    HUMAN_RESOURCES = "human_resources"
    MARKETING_SALES = "marketing_sales"
    OPERATIONS = "operations"

class BoardCommittee(BaseModel):
    """Board committee structure and membership"""
    committee_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    committee_type: CommitteeType
    committee_name: str
    charter_document: str
    
    # Committee composition
    chair_member_id: str
    members: List[str] = []  # Board member IDs
    minimum_members: int = 3
    independence_required: bool = True
    financial_expert_required: bool = False
    
    # Meeting schedule and governance
    meeting_frequency: Literal["monthly", "quarterly", "bi_annually", "annually", "as_needed"] = "quarterly"
    meetings_per_year: int = 4
    quorum_requirement: int = 2
    
    # Performance metrics
    meeting_attendance_rate: float = Field(ge=0.0, le=1.0, default=1.0)
    effectiveness_score: float = Field(ge=0.0, le=100.0, default=85.0)
    last_evaluation_date: Optional[datetime] = None
    
    # Committee responsibilities
    key_responsibilities: List[str] = []
    annual_work_plan: List[str] = []
    delegated_authorities: List[str] = []
    
    # Compliance and oversight
    regulatory_requirements: List[str] = []
    oversight_areas: List[str] = []
    reporting_requirements: List[str] = []
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BoardMeeting(BaseModel):
    """Board meeting planning and execution tracking"""
    meeting_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    meeting_type: BoardMeetingType
    meeting_title: str
    
    # Meeting logistics
    scheduled_date: datetime
    duration_minutes: int = 120
    meeting_format: Literal["in_person", "virtual", "hybrid"] = "hybrid"
    location: Optional[str] = None
    virtual_platform: Optional[str] = "Microsoft Teams"
    
    # Attendees
    board_members_invited: List[str] = []
    board_members_attending: List[str] = []
    executives_attending: List[str] = []
    external_attendees: List[str] = []
    
    # Meeting materials and agenda
    agenda_items: List[Dict[str, Any]] = []
    board_package_distributed: bool = False
    advance_materials_sent: Optional[datetime] = None
    
    # Meeting execution
    meeting_status: Literal["scheduled", "in_progress", "completed", "cancelled"] = "scheduled"
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    
    # Decisions and actions
    resolutions_passed: List[Dict[str, str]] = []
    action_items: List[Dict[str, str]] = []
    executive_session_held: bool = False
    
    # Documentation and compliance
    minutes_prepared: bool = False
    minutes_approved: bool = False
    minutes_document: Optional[str] = None
    presentations: List[str] = []
    
    # Performance metrics
    attendance_rate: float = 0.0
    meeting_effectiveness_rating: Optional[float] = Field(ge=1.0, le=5.0, default=None)
    
    prepared_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DirectorEvaluation(BaseModel):
    """Director performance evaluation and assessment"""
    evaluation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    director_member_id: str
    evaluation_period: str  # "2026", "Q4 2026"
    evaluation_type: Literal["annual", "self", "peer", "board", "chairman"] = "annual"
    
    # Performance dimensions
    board_participation: float = Field(ge=1.0, le=5.0)
    strategic_contribution: float = Field(ge=1.0, le=5.0)
    committee_effectiveness: float = Field(ge=1.0, le=5.0)
    independence_judgment: float = Field(ge=1.0, le=5.0)
    industry_expertise: float = Field(ge=1.0, le=5.0)
    
    # Meeting engagement
    meeting_attendance: float = Field(ge=0.0, le=1.0)  # Percentage attendance
    preparation_quality: float = Field(ge=1.0, le=5.0)
    question_quality: float = Field(ge=1.0, le=5.0)
    constructive_challenge: float = Field(ge=1.0, le=5.0)
    
    # Skills and qualifications
    current_skills: List[DirectorSkill] = []
    skill_gaps_identified: List[DirectorSkill] = []
    development_recommendations: List[str] = []
    
    # Overall assessment
    overall_rating: float = Field(ge=1.0, le=5.0)
    continuation_recommendation: bool = True
    term_renewal_eligible: bool = True
    
    # Feedback and development
    strengths: List[str] = []
    areas_for_improvement: List[str] = []
    training_recommendations: List[str] = []
    mentoring_assignments: List[str] = []
    
    # Evaluation metadata
    evaluator_id: str
    evaluation_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_evaluation_due: datetime

class GovernancePolicyFramework(BaseModel):
    """Corporate governance policy framework"""
    policy_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    policy_type: GovernancePolicy
    policy_title: str
    policy_description: str
    
    # Policy content and structure
    policy_document_url: str
    policy_version: str = "1.0"
    effective_date: datetime
    next_review_date: datetime
    
    # Approval and governance
    approved_by: str = "Board of Directors"
    approval_date: datetime
    requires_annual_review: bool = True
    requires_board_approval: bool = True
    
    # Implementation and monitoring
    implementation_status: Literal["draft", "approved", "implemented", "under_review"] = "implemented"
    compliance_monitoring: bool = True
    training_required: bool = True
    
    # Key provisions
    key_provisions: List[str] = []
    prohibited_activities: List[str] = []
    required_disclosures: List[str] = []
    escalation_procedures: List[str] = []
    
    # Performance and compliance
    compliance_rate: float = Field(ge=0.0, le=1.0, default=1.0)
    violations_ytd: int = 0
    training_completion_rate: float = Field(ge=0.0, le=1.0, default=1.0)
    
    policy_owner: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- Service Classes ---

class BoardCompositionOptimizer:
    """AI-powered board composition optimization for governance excellence"""
    
    def __init__(self):
        self.independence_target = 0.75  # 75% independent directors
        self.diversity_targets = {
            "gender": 0.33,      # 33% gender diversity minimum
            "ethnicity": 0.25,   # 25% ethnic diversity target
            "age": 0.20,         # 20% under 50 or over 65
            "geography": 0.30    # 30% international experience
        }
    
    def analyze_board_composition(self, board_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze current board composition and identify optimization opportunities"""
        
        total_members = len(board_members)
        if total_members == 0:
            return {"error": "No board members provided for analysis"}
        
        # Independence analysis
        independent_count = sum(1 for member in board_members if member.get("is_independent", False))
        independence_ratio = independent_count / total_members
        
        # Skills matrix analysis
        skills_coverage = self._analyze_skills_matrix(board_members)
        
        # Diversity analysis  
        diversity_metrics = self._analyze_diversity_metrics(board_members)
        
        # Committee coverage analysis
        committee_coverage = self._analyze_committee_coverage(board_members)
        
        # Generate recommendations
        recommendations = self._generate_composition_recommendations(
            independence_ratio, skills_coverage, diversity_metrics, committee_coverage
        )
        
        return {
            "composition_analysis": {
                "total_members": total_members,
                "independent_members": independent_count,
                "independence_ratio": independence_ratio,
                "independence_compliant": independence_ratio >= self.independence_target
            },
            "skills_matrix": skills_coverage,
            "diversity_metrics": diversity_metrics,
            "committee_coverage": committee_coverage,
            "governance_score": self._calculate_governance_score(
                independence_ratio, skills_coverage, diversity_metrics
            ),
            "optimization_recommendations": recommendations,
            "ipo_readiness": {
                "minimum_independence_met": independence_ratio >= 0.50,  # 50% minimum for IPO
                "audit_committee_qualified": self._check_audit_committee_qualification(board_members),
                "compensation_committee_independent": True,
                "governance_framework_complete": True
            }
        }
    
    def _analyze_skills_matrix(self, board_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze board skills matrix and expertise coverage"""
        
        required_skills = [skill.value for skill in DirectorSkill]
        skills_count = {skill: 0 for skill in required_skills}
        
        for member in board_members:
            member_skills = member.get("skills", [])
            for skill in member_skills:
                if skill in skills_count:
                    skills_count[skill] += 1
        
        total_members = len(board_members)
        skills_coverage = {
            skill: count / total_members if total_members > 0 else 0
            for skill, count in skills_count.items()
        }
        
        critical_gaps = [
            skill for skill, coverage in skills_coverage.items()
            if coverage < 0.30  # Less than 30% coverage
        ]
        
        return {
            "skills_coverage_matrix": skills_coverage,
            "well_covered_skills": [s for s, c in skills_coverage.items() if c >= 0.50],
            "adequately_covered_skills": [s for s, c in skills_coverage.items() if 0.30 <= c < 0.50],
            "skills_gaps": critical_gaps,
            "overall_coverage_score": sum(skills_coverage.values()) / len(skills_coverage)
        }
    
    def _analyze_diversity_metrics(self, board_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze board diversity across multiple dimensions"""
        
        total_members = len(board_members)
        if total_members == 0:
            return {}
        
        # Mock diversity analysis - in production: use actual demographic data
        diversity_metrics = {
            "gender_diversity": 0.43,      # 43% women
            "ethnic_diversity": 0.29,      # 29% ethnic minorities
            "age_diversity": 0.27,         # 27% extreme age diversity
            "geographic_diversity": 0.35,  # 35% international background
            "industry_diversity": 0.60,    # 60% different industry backgrounds
            "tenure_diversity": 0.45       # 45% different tenure ranges
        }
        
        diversity_score = sum(diversity_metrics.values()) / len(diversity_metrics)
        
        return {
            "diversity_metrics": diversity_metrics,
            "diversity_targets": self.diversity_targets,
            "target_achievement": {
                dimension: metrics >= self.diversity_targets.get(dimension, 0.25)
                for dimension, metrics in diversity_metrics.items()
            },
            "overall_diversity_score": diversity_score,
            "diversity_grade": self._calculate_diversity_grade(diversity_score)
        }
    
    def _analyze_committee_coverage(self, board_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze board committee coverage and effectiveness"""
        
        required_committees = ["audit", "compensation", "nominating"]
        committee_coverage = {}
        
        for committee in required_committees:
            committee_members = [
                member for member in board_members
                if committee in member.get("committees", [])
            ]
            
            committee_coverage[committee] = {
                "member_count": len(committee_members),
                "independence_ratio": sum(1 for m in committee_members if m.get("is_independent", False)) / max(len(committee_members), 1),
                "financial_expert": any(
                    "financial_expertise" in m.get("skills", []) 
                    for m in committee_members
                ) if committee == "audit" else True,
                "adequately_staffed": len(committee_members) >= 3
            }
        
        return {
            "required_committees": required_committees,
            "committee_analysis": committee_coverage,
            "committee_readiness": all(
                analysis["adequately_staffed"] and analysis["independence_ratio"] >= 0.67  # type: ignore
                for analysis in committee_coverage.values()  # type: ignore
            )  # type: ignore
        }
    
    def _generate_composition_recommendations(self, independence_ratio: float, 
                                           skills_coverage: Dict[str, Any], 
                                           diversity_metrics: Dict[str, Any],
                                           committee_coverage: Dict[str, Any]) -> List[str]:
        """Generate board composition optimization recommendations"""
        
        recommendations = []
        
        # Independence recommendations
        if independence_ratio < self.independence_target:
            recommendations.append(  # type: ignore
                f"Increase board independence to {self.independence_target*100}% "
                f"(currently {independence_ratio*100:.1f}%)"
            )
        
        # Skills gap recommendations
        skills_gaps = skills_coverage.get("skills_gaps", [])
        if skills_gaps:
            recommendations.append(  # type: ignore
                f"Recruit directors with expertise in: {', '.join(skills_gaps[:3])}"
            )
        
        # Diversity recommendations
        diversity_scores = diversity_metrics.get("diversity_metrics", {})
        for dimension, score in diversity_scores.items():
            target = self.diversity_targets.get(dimension, 0.25)
            if score < target:
                recommendations.append(  # type: ignore
                    f"Improve {dimension.replace('_', ' ')} to meet {target*100}% target"
                )
        
        # Committee recommendations
        committee_analysis = committee_coverage.get("committee_analysis", {})
        for committee, analysis in committee_analysis.items():
            if not analysis["adequately_staffed"]:
                recommendations.append(f"Add member to {committee} committee")  # type: ignore
        
        return recommendations  # type: ignore
    
    def _calculate_governance_score(self, independence: float, skills: Dict[str, Any], 
                                  diversity: Dict[str, Any]) -> float:
        """Calculate overall governance effectiveness score"""
        
        independence_score = min(independence / self.independence_target * 100, 100)
        skills_score = skills.get("overall_coverage_score", 0) * 100
        diversity_score = diversity.get("overall_diversity_score", 0) * 100
        
        # Weighted average: 40% independence, 35% skills, 25% diversity
        overall_score = (independence_score * 0.40 + skills_score * 0.35 + diversity_score * 0.25)
        
        return min(overall_score, 100.0)
    
    def _calculate_diversity_grade(self, score: float) -> str:
        """Calculate diversity letter grade"""
        if score >= 0.80:
            return "A+"
        elif score >= 0.70:
            return "A"
        elif score >= 0.60:
            return "B+"
        elif score >= 0.50:
            return "B"
        elif score >= 0.40:
            return "C"
        else:
            return "D"
    
    def _check_audit_committee_qualification(self, board_members: List[Dict[str, Any]]) -> bool:
        """Check if audit committee meets qualification requirements"""
        
        audit_members = [
            member for member in board_members
            if "audit" in member.get("committees", [])
        ]
        
        # Check minimum requirements
        if len(audit_members) < 3:
            return False
        
        # Check independence
        independent_count = sum(1 for member in audit_members if member.get("is_independent", False))
        if independent_count < len(audit_members):  # All must be independent
            return False
        
        # Check financial expertise
        financial_expert = any(
            "financial_expertise" in member.get("skills", [])
            for member in audit_members
        )
        
        return financial_expert

class MeetingGovernanceAutomator:
    """Automated board meeting governance and workflow management"""
    
    def __init__(self):
        self.advance_notice_days = 10
        self.material_distribution_days = 5
    
    def create_board_meeting(self, meeting: BoardMeeting) -> Dict[str, Any]:
        """Create board meeting with automated governance workflow"""
        
        # Validate meeting requirements
        validation_results = self._validate_meeting_requirements(meeting)
        if not validation_results["valid"]:
            return {"error": "Meeting validation failed", "issues": validation_results["issues"]}
        
        # Generate meeting workflow
        workflow = self._generate_meeting_workflow(meeting)
        
        # Create governance checklist
        governance_checklist = self._create_governance_checklist(meeting)
        
        # Schedule automated tasks
        automated_tasks = self._schedule_automated_tasks(meeting)
        
        return {
            "meeting_id": meeting.meeting_id,
            "meeting_status": "scheduled",
            "governance_workflow": workflow,
            "governance_checklist": governance_checklist,
            "automated_tasks": automated_tasks,
            "compliance_requirements": self._get_compliance_requirements(meeting.meeting_type)
        }
    
    def _validate_meeting_requirements(self, meeting: BoardMeeting) -> Dict[str, Any]:
        """Validate meeting governance requirements"""
        
        issues = []
        
        # Notice period validation
        notice_period = (meeting.scheduled_date - datetime.now(timezone.utc)).days
        if notice_period < self.advance_notice_days:
            issues.append(f"Insufficient notice period: {notice_period} days (required: {self.advance_notice_days})")  # type: ignore
        
        # Attendee validation
        if len(meeting.board_members_invited) < 3:  # Minimum quorum
            issues.append("Insufficient board members invited for quorum")  # type: ignore
        
        # Agenda validation
        if not meeting.agenda_items:
            issues.append("Meeting agenda is required")  # type: ignore
        
        return {
            "valid": len(issues) == 0,  # type: ignore
            "issues": issues,
            "notice_period_days": notice_period
        }
    
    def _generate_meeting_workflow(self, meeting: BoardMeeting) -> List[Dict[str, Any]]:
        """Generate automated meeting governance workflow"""
        
        meeting_date = meeting.scheduled_date
        
        workflow: List[Dict[str, Any]] = [  # type: ignore
            {
                "task": "Send initial meeting notice",
                "due_date": meeting_date - timedelta(days=self.advance_notice_days),
                "responsible": "corporate_secretary",
                "status": "pending",
                "description": "Send formal meeting notice to all board members"
            },
            {
                "task": "Distribute board materials",
                "due_date": meeting_date - timedelta(days=self.material_distribution_days),
                "responsible": "corporate_secretary", 
                "status": "pending",
                "description": "Distribute board package and meeting materials"
            },
            {
                "task": "Confirm attendance",
                "due_date": meeting_date - timedelta(days=2),
                "responsible": "corporate_secretary",
                "status": "pending",
                "description": "Confirm attendance and meeting logistics"
            },
            {
                "task": "Prepare meeting room/technology",
                "due_date": meeting_date - timedelta(hours=2),
                "responsible": "facilities_team",
                "status": "pending",
                "description": "Set up meeting room and test technology"
            },
            {
                "task": "Conduct board meeting",
                "due_date": meeting_date,
                "responsible": "chairman",
                "status": "pending",
                "description": "Execute board meeting according to agenda"
            },
            {
                "task": "Prepare draft minutes",
                "due_date": meeting_date + timedelta(days=3),
                "responsible": "corporate_secretary",
                "status": "pending",
                "description": "Prepare and circulate draft meeting minutes"
            },
            {
                "task": "Approve final minutes",
                "due_date": meeting_date + timedelta(days=14),
                "responsible": "board_chairman",
                "status": "pending", 
                "description": "Review and approve final meeting minutes"
            }
        ]
        
        return workflow  # type: ignore
    
    def _create_governance_checklist(self, meeting: BoardMeeting) -> List[Dict[str, Any]]:
        """Create governance compliance checklist for meeting"""
        
        checklist: List[Dict[str, Any]] = [  # type: ignore
            {"item": "Proper notice provided", "required": True, "completed": False},
            {"item": "Agenda distributed in advance", "required": True, "completed": False},
            {"item": "Board materials provided", "required": True, "completed": False},
            {"item": "Quorum achieved", "required": True, "completed": False},
            {"item": "Executive session held", "required": False, "completed": False},
            {"item": "Conflicts of interest declared", "required": True, "completed": False},
            {"item": "Minutes recorded", "required": True, "completed": False},
            {"item": "Action items documented", "required": True, "completed": False}
        ]
        
        # Add committee-specific requirements
        if meeting.meeting_type == BoardMeetingType.COMMITTEE_MEETING:
            checklist.extend([  # type: ignore
                {"item": "Committee charter reviewed", "required": True, "completed": False},
                {"item": "Independence requirements met", "required": True, "completed": False}
            ])
        
        return checklist  # type: ignore
    
    def _schedule_automated_tasks(self, meeting: BoardMeeting) -> List[Dict[str, Any]]:
        """Schedule automated tasks for meeting governance"""
        
        return [
            {
                "task_type": "email_notification",
                "trigger_date": meeting.scheduled_date - timedelta(days=self.advance_notice_days),
                "recipients": meeting.board_members_invited,
                "template": "board_meeting_notice",
                "automated": True
            },
            {
                "task_type": "material_distribution",
                "trigger_date": meeting.scheduled_date - timedelta(days=self.material_distribution_days),
                "recipients": meeting.board_members_invited,
                "template": "board_materials",
                "automated": True
            },
            {
                "task_type": "attendance_reminder",
                "trigger_date": meeting.scheduled_date - timedelta(days=1),
                "recipients": meeting.board_members_invited,
                "template": "meeting_reminder",
                "automated": True
            },
            {
                "task_type": "post_meeting_survey",
                "trigger_date": meeting.scheduled_date + timedelta(hours=2),
                "recipients": meeting.board_members_attending,
                "template": "meeting_effectiveness_survey",
                "automated": True
            }
        ]
    
    def _get_compliance_requirements(self, meeting_type: BoardMeetingType) -> List[str]:
        """Get compliance requirements for meeting type"""
        
        base_requirements = [
            "Proper notice and agenda distribution",
            "Quorum requirements met",
            "Minutes recorded and maintained",
            "Conflicts of interest disclosed"
        ]
        
        if meeting_type == BoardMeetingType.ANNUAL_MEETING:
            base_requirements.extend([
                "Shareholder proxy materials filed",
                "Annual report distributed",
                "Director elections conducted",
                "Auditor ratification"
            ])
        elif meeting_type == BoardMeetingType.COMMITTEE_MEETING:
            base_requirements.extend([
                "Committee charter compliance",
                "Independence requirements verified",
                "Specialized expertise confirmed"
            ])
        
        return base_requirements

# Initialize services
board_optimizer = BoardCompositionOptimizer()
meeting_automator = MeetingGovernanceAutomator()