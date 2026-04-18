"""
SelfMate AI Agent - The autonomous financial advisor for MyNetTax.

This is the core AI agent that provides personalized financial advice,
automates tasks, and helps users achieve their financial goals.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import openai  # type: ignore

# LangChain is an optional dependency — guard the import so the service
# still starts when the package is absent (e.g. in unit-test environments).
try:
    from langchain.agents import AgentExecutor  # type: ignore
    from langchain.agents.openai_assistant import (
        OpenAIAssistantRunnable,  # type: ignore
    )
    from langchain.memory import ConversationBufferWindowMemory  # type: ignore
    from langchain.schema import AIMessage, HumanMessage, SystemMessage  # type: ignore
    from langchain.tools import BaseTool  # type: ignore
except ImportError:  # pragma: no cover
    AgentExecutor = None  # type: ignore
    OpenAIAssistantRunnable = None  # type: ignore
    ConversationBufferWindowMemory = None  # type: ignore
    AIMessage = HumanMessage = SystemMessage = None  # type: ignore
    BaseTool = None  # type: ignore

from ..memory.memory_manager import MemoryManager
from ..tools.tool_registry import ToolRegistry

# ISO-639-1 code → full language name for GPT system prompt injection
_LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pl": "Polish",
    "ro": "Romanian",
    "uk": "Ukrainian",
    "zh": "Chinese",
    "ar": "Arabic",
}


def _mortgage_advisor_prompt_addon() -> str:
    return """
MORTGAGE READINESS MODE (activated):
- You help UK self-employed users understand mortgage **readiness** in general terms only.
- This is **not** regulated mortgage advice: do **not** recommend a specific lender, product, or rate; do not say the user "will" be approved.
- Useful UK patterns to mention when relevant: employed multiples are often quoted around **4–4.5×** income; self-employed lending is often **more conservative** (commonly **~3–4×** on verified profits, varies by lender); lenders typically want **1–3 years** of accounts / SA302 / tax year overviews; minimum deposits are often **~5–15%** depending on credit and product availability.
- If the case is complex (adverse credit, visa, limited company retained profit, recent business change) or the user needs an offer, suggest speaking with a **whole-of-market mortgage broker** and using MyNetTax mortgage tools where available.
- Personalise using USER PROFILE and FINANCIAL CONTEXT (income, profit, tax, deposit in context if present).
"""


def _language_instruction(lang: str) -> str:
    """Return a system-prompt instruction forcing the response language."""
    name = _LANGUAGE_NAMES.get(lang.lower(), lang)
    if lang.lower() == "en":
        return ""  # default, no extra instruction needed
    return f"\n\nIMPORTANT: You MUST respond entirely in {name}. All text — explanations, recommendations, and labels — must be in {name}."


@dataclass
class AgentResponse:
    """Response from SelfMate Agent"""
    response: str
    actions_taken: List[str]
    recommendations: List[str]
    confidence_score: float
    insights: List[Dict[str, Any]]
    next_actions: List[str]


class SelfMateAgent:
    """
    SelfMate - Autonomous AI Financial Advisor

    SelfMate is an intelligent agent that:
    - Provides personalized financial advice
    - Automates routine financial tasks
    - Monitors financial health proactively
    - Offers strategic business guidance
    - Learns from user interactions
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        tool_registry: ToolRegistry,
        openai_api_key: str,
        model: str = "gpt-4-turbo-preview"
    ):
        self.memory_manager = memory_manager
        self.tool_registry = tool_registry
        self.model = model
        self.start_time = datetime.now(timezone.utc)

        # Initialize OpenAI client
        self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)  # type: ignore

        # Agent configuration
        self.personality = self._load_personality()
        self.capabilities = self._initialize_capabilities()

        # Performance tracking
        self.interaction_count = 0
        self.success_rate = 0.0
        self.avg_response_time = 0.0

        print("🤖 SelfMate Agent initialized with advanced financial intelligence!")

    def _load_personality(self) -> Dict[str, str]:
        """Load SelfMate's personality configuration"""
        return {
            "name": "SelfMate",
            "role": "Personal Financial Advisor and Business Partner",
            "personality": """You are SelfMate, an expert AI financial advisor specializing in UK self-employed professionals.
            You are proactive, empathetic, and highly knowledgeable about:
            - UK tax regulations and HMRC compliance
            - Business growth strategies for SMEs
            - Financial planning and cash flow optimization
            - Investment advice and wealth building
            - Risk management and fraud prevention

            Your communication style is:
            - Professional yet friendly and approachable
            - Clear and actionable in recommendations
            - Proactive in identifying opportunities
            - Empathetic to financial stress and concerns
            - Confident in your expertise but humble about limitations

            You have access to comprehensive financial data and can take actions across
            the entire MyNetTax platform to help users achieve their goals.""",

            "guidelines": """
            1. Always provide specific, actionable advice
            2. Reference actual user data when making recommendations
            3. Proactively identify opportunities and risks
            4. Explain complex financial concepts simply
            5. Offer step-by-step implementation plans
            6. Be transparent about assumptions and limitations
            7. Celebrate user achievements and progress
            8. Maintain strict confidentiality and data protection
            """
        }

    def _initialize_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Initialize SelfMate's core capabilities"""
        return {
            "financial_analysis": {
                "description": "Deep financial health assessment and optimization",
                "confidence": 0.92,
                "tools": ["transactions_analysis", "cash_flow_prediction", "profit_analysis"]
            },
            "tax_optimization": {
                "description": "UK tax planning and HMRC compliance automation",
                "confidence": 0.88,
                "tools": ["tax_calculation", "allowance_optimization", "compliance_check"]
            },
            "business_growth": {
                "description": "Strategic business advice and market insights",
                "confidence": 0.85,
                "tools": ["market_analysis", "competition_research", "growth_planning"]
            },
            "risk_management": {
                "description": "Financial risk assessment and mitigation",
                "confidence": 0.94,
                "tools": ["fraud_detection", "risk_scoring", "insurance_analysis"]
            },
            "automation": {
                "description": "Task automation and workflow optimization",
                "confidence": 0.91,
                "tools": ["invoice_automation", "payment_reminders", "calendar_management"]
            },
            "investment_advice": {
                "description": "Personal investment and wealth building guidance",
                "confidence": 0.83,
                "tools": ["portfolio_analysis", "investment_research", "pension_optimization"]
            }
        }

    async def process_message(
        self,
        user_id: str,
        message: str,
        language: str = "en",
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process user message and generate intelligent response.

        language: ISO-639-1 code (en, ru, de, fr, es …)
                  The agent will respond entirely in the chosen language.
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Load user context and history
            user_profile = await self.memory_manager.get_user_profile(user_id)
            conversation_history = await self.memory_manager.get_recent_conversations(user_id, limit=10)
            financial_context = await self.memory_manager.get_financial_context(user_id)

            # Analyze message intent and extract requirements
            intent = await self._analyze_message_intent(message, language=language, context=context)

            advisor_mode = (
                str((context or {}).get("advisor_mode") or "").strip().lower() or None
            )

            # Generate comprehensive response
            response_data = await self._generate_response(
                user_id=user_id,
                message=message,
                language=language,
                intent=intent,
                user_profile=user_profile,
                financial_context=financial_context,
                conversation_history=conversation_history,
                advisor_mode=advisor_mode,
            )

            # Execute any required actions
            actions_taken = await self._execute_actions(user_id, response_data.get("actions", []))

            # Generate proactive recommendations
            recommendations = await self._generate_recommendations(user_id, financial_context)

            # Calculate confidence score
            confidence_score = self._calculate_confidence(intent, user_profile, response_data)

            # Update interaction metrics
            self.interaction_count += 1
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._update_performance_metrics(processing_time, True)

            return AgentResponse(
                response=response_data["response"],
                actions_taken=actions_taken,
                recommendations=recommendations,
                confidence_score=confidence_score,
                insights=response_data.get("insights", []),
                next_actions=response_data.get("next_actions", [])
            )

        except Exception as e:
            self._update_performance_metrics(0, False)
            raise Exception(f"Agent processing error: {str(e)}")

    async def _analyze_message_intent(
        self,
        message: str,
        language: str = "en",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze user message to understand intent and classify request type"""

        lang_instruction = _language_instruction(language)
        system_prompt = f"""
        You are analyzing user messages to understand their financial intent.
        Classify the message into these categories and extract key information:

        Categories:
        - financial_query: Questions about finances, transactions, or financial health
        - tax_question: Tax-related queries, deductions, HMRC compliance
        - business_advice: Strategic business questions, growth planning
        - automation_request: Requests to automate tasks or set up processes
        - urgent_issue: Urgent financial problems requiring immediate attention
        - general_chat: Casual conversation or gratitude expressions

        Extract:
        - urgency_level (low/medium/high/critical)
        - specific_topics mentioned
        - action_items requested
        - emotional_tone (stressed/concerned/neutral/positive)
        - data_requirements (what user data might be needed)

        Respond with JSON only.
        """
        if lang_instruction:
            system_prompt = system_prompt.rstrip() + lang_instruction

        try:
            response = await self.openai_client.chat.completions.create(  # type: ignore
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Message: {message}\nContext: {json.dumps(context or {})}"}
                ],
                temperature=0.1,
                max_tokens=500
            )

            intent = json.loads(response.choices[0].message.content)  # type: ignore
            return intent

        except Exception:
            # Fallback intent analysis
            return {
                "category": "general_chat",
                "urgency_level": "low",
                "specific_topics": [],
                "action_items": [],
                "emotional_tone": "neutral",
                "data_requirements": []
            }

    async def _generate_response(
        self,
        user_id: str,
        message: str,
        intent: Dict[str, Any],
        user_profile: Dict[str, Any],
        financial_context: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        language: str = "en",
        advisor_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive response using GPT-4 with full context"""

        # Build comprehensive context for the agent
        context_summary = f"""
        USER PROFILE:
        - Business Type: {user_profile.get('business_type', 'Unknown')}
        - Annual Revenue: £{user_profile.get('annual_revenue', 0):,.0f}
        - Primary Concerns: {', '.join(user_profile.get('concerns', []))}

        FINANCIAL CONTEXT:
        - Current Balance: £{financial_context.get('current_balance', 0):,.2f}
        - Monthly Profit: £{financial_context.get('monthly_profit', 0):,.2f}
        - Tax Due: £{financial_context.get('tax_due', 0):,.2f}
        - Key Metrics: {json.dumps(financial_context.get('metrics', {}), indent=2)}

        CONVERSATION HISTORY:
        {json.dumps(conversation_history[-5:], indent=2) if conversation_history else "No previous conversations"}

        MESSAGE INTENT:
        {json.dumps(intent, indent=2)}
        """

        mode_addon = (
            _mortgage_advisor_prompt_addon()
            if advisor_mode == "mortgage"
            else ""
        )

        system_prompt = f"""
        {self.personality['personality']}

        {self.personality['guidelines']}
        {mode_addon}

        You have access to the user's complete financial picture through these tools:
        {json.dumps(list(self.tool_registry.get_available_tools().keys()) if self.tool_registry else [], indent=2)}

        Current Context:
        {context_summary}

        Your response should:
        1. Address the user's specific question or concern
        2. Provide actionable recommendations based on their data
        3. Identify opportunities for optimization or improvement
        4. Offer to take specific actions if helpful
        5. Be encouraging and supportive

        Respond with JSON containing:
        - response: Your conversational response to the user
        - actions: List of actions you recommend taking (tools to call)
        - insights: Key insights discovered from the analysis
        - next_actions: Suggestions for future actions or follow-ups
        {_language_instruction(language)}
        """

        try:
            response = await self.openai_client.chat.completions.create(  # type: ignore
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            result = json.loads(response.choices[0].message.content)  # type: ignore
            return result

        except Exception:
            # Fallback response
            return {
                "response": f"I understand you're asking about {intent.get('category', 'your finances')}. Let me help you with that. Based on your profile, I can provide some insights, but I'm experiencing a technical issue at the moment. Please try asking again, or I can help you with a specific financial task.",
                "actions": [],
                "insights": [],
                "next_actions": ["retry_request", "contact_support"]
            }

    async def _execute_actions(self, user_id: str, actions: List[str]) -> List[str]:
        """Execute requested actions using available tools"""
        executed_actions: List[str] = []

        if not self.tool_registry:
            return executed_actions

        for action in actions:
            try:
                # Map action to available tools
                tool = self.tool_registry.get_tool(action)
                if tool:
                    result = await tool.execute(user_id=user_id)
                    executed_actions.append(f"✅ {action}: {result.get('status', 'completed')}")  # type: ignore
                else:
                    executed_actions.append(f"⚠️ {action}: Tool not available")  # type: ignore

            except Exception as e:
                executed_actions.append(f"❌ {action}: Failed - {str(e)}")  # type: ignore

        return executed_actions

    async def _generate_recommendations(
        self,
        user_id: str,
        financial_context: Dict[str, Any]
    ) -> List[str]:
        """Generate proactive recommendations based on user's financial situation"""

        recommendations: List[str] = []

        # Cash flow recommendations
        if financial_context.get('current_balance', 0) < 1000:  # type: ignore
            recommendations.append("💰 Consider setting up payment reminders for overdue invoices")  # type: ignore

        # Tax optimization
        tax_due = financial_context.get('tax_due', 0)  # type: ignore
        if tax_due > 5000:
            recommendations.append(f"📊 You have £{tax_due:,.0f} in upcoming tax payments - let me help optimize this")  # type: ignore

        # Business growth
        monthly_profit = financial_context.get('monthly_profit', 0)  # type: ignore
        if monthly_profit > 0:
            recommendations.append(f"📈 With £{monthly_profit:,.0f} monthly profit, consider investment opportunities")  # type: ignore

        # Generic helpful suggestions
        recommendations.extend([  # type: ignore
            "📱 Set up automated expense categorization to save time",
            "📅 Schedule quarterly business review to track progress",
            "🎯 Review your financial goals and adjust strategies"
        ])

        return recommendations[:3]  # Limit to top 3

    def _calculate_confidence(
        self,
        intent: Dict[str, Any],
        user_profile: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for the response"""

        base_confidence = 0.8

        # Adjust based on user profile completeness
        profile_completeness = len([v for v in user_profile.values() if v]) / max(len(user_profile), 1)  # type: ignore
        confidence_adjustment = profile_completeness * 0.1

        # Adjust based on intent clarity
        if intent.get('urgency_level') in ['high', 'critical']:  # type: ignore
            confidence_adjustment += 0.05

        # Adjust based on available actions
        if response_data.get('actions'):  # type: ignore
            confidence_adjustment += 0.05

        return min(base_confidence + confidence_adjustment, 0.98)

    def _update_performance_metrics(self, processing_time: float, success: bool):
        """Update agent performance metrics"""
        # Update average response time
        if self.interaction_count > 0:
            self.avg_response_time = (
                (self.avg_response_time * (self.interaction_count - 1) + processing_time)
                / self.interaction_count
            )
        else:
            self.avg_response_time = processing_time

        # Update success rate (guard against division by zero on first error)
        if self.interaction_count > 0:
            if success:
                self.success_rate = (self.success_rate * (self.interaction_count - 1) + 1.0) / self.interaction_count
            else:
                self.success_rate = (self.success_rate * (self.interaction_count - 1)) / self.interaction_count
        else:
            self.success_rate = 1.0 if success else 0.0

    async def generate_proactive_insights(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate proactive insights and recommendations for user"""

        # Get user's financial context
        # Get memory data for insights (variables currently unused but reserved for future features)
        _ = await self.memory_manager.get_financial_context(user_id)
        _ = await self.memory_manager.get_user_profile(user_id)

        insights: List[Dict[str, Any]] = []

        # Example proactive insights
        insights.append({  # type: ignore
            "type": "cash_flow_alert",
            "title": "Cash Flow Optimization Opportunity",
            "description": "I noticed you could improve your cash flow by 15% with strategic invoice timing.",
            "priority": "medium",
            "potential_impact": "£2,400 annually",
            "action_required": "Review payment terms with major clients"
        })

        insights.append({  # type: ignore
            "type": "tax_saving",
            "title": "Tax Allowance Opportunity",
            "description": "You haven't claimed your full home office allowance this year.",
            "priority": "high",
            "potential_impact": "£1,200 tax savings",
            "action_required": "Update expense categories for home office costs"
        })

        return insights

    async def process_feedback(
        self,
        user_id: str,
        message_id: str,
        rating: int,
        feedback: Optional[str] = None
    ) -> None:
        """Process user feedback for agent improvement"""

        feedback_data: Dict[str, Any] = {
            "user_id": user_id,
            "message_id": message_id,
            "rating": rating,
            "feedback": feedback,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Store feedback for learning
        await self.memory_manager.store_feedback(feedback_data)

        # Adjust agent parameters based on feedback
        if rating <= 2:
            # Low rating - flag for review
            print(f"⚠️ Low rating ({rating}) received from user {user_id}")

    def is_ready(self) -> bool:
        """Check if agent is fully initialized and ready"""
        return (
            self.memory_manager is not None and  # type: ignore
            self.tool_registry is not None and  # type: ignore
            self.openai_client is not None  # type: ignore
        )

    def get_uptime_hours(self) -> float:
        """Get agent uptime in hours"""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            "uptime_hours": self.get_uptime_hours(),
            "total_interactions": self.interaction_count,
            "success_rate": self.success_rate,
            "avg_response_time_s": self.avg_response_time,
            "capabilities": self.capabilities,
            "model": self.model,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    async def schedule_retraining(self):
        """Schedule agent retraining based on accumulated feedback"""
        # TODO: Implement model fine-tuning pipeline
        print("🔄 Agent retraining scheduled - this feature is in development")
        pass
