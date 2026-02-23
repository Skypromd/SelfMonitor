"""
Conversation Manager for SelfMate AI Agent

Manages conversation sessions, context, and dialogue flow.
Provides seamless conversation experience with memory and context awareness.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
import uuid

from ..memory.memory_manager import MemoryManager


class ConversationManager:
    """
    Advanced conversation management for SelfMate Agent
    
    Features:
    - Session management and context preservation
    - Conversation history tracking
    - Context-aware dialogue flow
    - Multi-turn conversation support
    - Personalization and user preferences
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.conversation_templates = self._load_conversation_templates()
        
    def _load_conversation_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load conversation templates for different scenarios"""
        return {
            "welcome": {
                "message": "Hello! I'm SelfMate, your AI financial advisor. I'm here to help you optimize your finances, grow your business, and achieve your goals. How can I assist you today?",
                "suggestions": [
                    "Analyze my financial health",
                    "Help me with tax planning", 
                    "Review my business performance",
                    "Set up automated workflows"
                ]
            },
            "returning_user": {
                "message": "Welcome back! I've been monitoring your financial situation and have some insights to share. What would you like to focus on today?",
                "suggestions": [
                    "Show me recent insights",
                    "Update my financial goals",
                    "Review automated tasks",
                    "Check for new opportunities"
                ]
            },
            "urgent_issue": {
                "message": "I notice this seems urgent. Let me prioritize your request and provide immediate assistance.",
                "suggestions": [
                    "Get immediate help",
                    "Escalate to human support",
                    "Take emergency action",
                    "Access emergency resources"
                ]
            },
            "follow_up": {
                "message": "Following up on our previous conversation, here's what I've found:",
                "suggestions": [
                    "See the results",
                    "Take next steps",
                    "Modify the plan",
                    "Get more details"
                ]
            }
        }
    
    async def get_conversation_context(
        self, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive conversation context for user"""
        
        # Get user profile and preferences
        user_profile = await self.memory_manager.get_user_profile(user_id)  # type: ignore
        
        # Get recent conversation history
        recent_conversations = await self.memory_manager.get_recent_conversations(user_id, limit=5)  # type: ignore
        
        # Get financial context
        financial_context = await self.memory_manager.get_financial_context(user_id)  # type: ignore
        
        # Determine conversation type
        conversation_type = self._determine_conversation_type(
            user_profile, 
            recent_conversations,
            financial_context
        )
        
        # Get session-specific context
        session_context = {}
        if session_id:
            session_context = await self.memory_manager.get_session(session_id) or {}  # type: ignore
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "conversation_type": conversation_type,
            "user_profile": user_profile,
            "recent_conversations": recent_conversations,
            "financial_context": financial_context,
            "session_context": session_context,
            "context_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _determine_conversation_type(
        self, 
        user_profile: Dict[str, Any],
        recent_conversations: List[Dict[str, Any]],
        financial_context: Dict[str, Any]
    ) -> str:
        """Determine the type of conversation based on context"""
        
        # Check if this is a new user
        if not recent_conversations:
            return "welcome"
        
        # Check for urgent financial situations
        cash_flow = financial_context.get("current_balance", 0)
        if cash_flow < 500:  # Low cash warning
            return "urgent_issue"
        
        # Check for follow-up conversations
        last_conversation = recent_conversations[0] if recent_conversations else {}
        last_conversation_time = last_conversation.get("timestamp")
        
        if last_conversation_time:
            last_time = datetime.fromisoformat(last_conversation_time.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) - last_time.replace(tzinfo=None) < timedelta(hours=24):
                return "follow_up"
        
        return "returning_user"
    
    async def start_conversation(
        self, 
        user_id: str, 
        initial_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start new conversation session"""
        
        # Create new session
        session_id = await self.memory_manager.create_session(user_id)  # type: ignore
        
        # Get conversation context
        context = await self.get_conversation_context(user_id, session_id)
        
        # Generate welcome message based on context
        welcome_data = self._generate_welcome_message(context)
        
        # Store session in active sessions
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "turn_count": 0,
            "context": context
        }
        
        return {
            "session_id": session_id,
            "welcome_message": welcome_data["message"],
            "suggestions": welcome_data["suggestions"],
            "context": context
        }
    
    def _generate_welcome_message(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate personalized welcome message"""
        
        conversation_type = context.get("conversation_type", "welcome")
        template = self.conversation_templates.get(conversation_type, self.conversation_templates["welcome"])
        
        # Personalize based on user profile
        user_profile = context.get("user_profile", {})
        user_name = user_profile.get("first_name", "")
        business_type = user_profile.get("business_type", "")
        
        message = template["message"]
        
        # Add personalization
        if user_name:
            if conversation_type == "welcome":
                message = f"Hello {user_name}! " + message
            else:
                message = f"Hello {user_name}! " + message
        
        if business_type and business_type != "Unknown":
            message += f" I see you're in {business_type} - I have specialized expertise in this area."
        
        return {
            "message": message,
            "suggestions": template["suggestions"]
        }
    
    async def save_conversation_turn(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save a complete conversation turn"""
        
        # Create conversation turn data
        turn_data: Dict[str, Any] = {
            "turn_id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_id": session_id,
            "user_message": user_message,
            "agent_response": agent_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        # Store in memory system
        await self.memory_manager.store_conversation(  # type: ignore
            user_id=user_id,
            user_message=user_message,
            agent_response=agent_response,
            metadata=metadata
        )
        
        # Update session in active sessions
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["turn_count"] += 1
            self.active_sessions[session_id]["last_activity"] = datetime.now(timezone.utc).isoformat()
            self.active_sessions[session_id]["last_turn"] = turn_data
    
    async def get_conversation_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a specific session"""
        
        # Get conversation history from memory
        conversations = await self.memory_manager.get_recent_conversations(user_id, limit=limit)  # type: ignore
        
        # Filter by session if specified
        session_conversations: List[Dict[str, Any]] = []
        for conv in conversations:
            if conv.get("session_id") == session_id or not session_id:
                session_conversations.append({
                    "timestamp": conv["timestamp"],
                    "user_message": conv["user_message"],
                    "agent_response": conv["agent_response"],
                    "metadata": conv.get("metadata", {})
                })
        
        return session_conversations
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        # Clean up expired sessions
        self._cleanup_expired_sessions()
        return len(self.active_sessions)
    
    async def get_total_conversation_count(self) -> int:
        """Get total number of conversations across all users"""
        # This would typically query the memory system
        # For now, return a mock count
        return len(self.active_sessions) * 10  # Estimate
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions from active sessions"""
        current_time = datetime.now(timezone.utc)
        expired_sessions: List[str] = []
        
        for session_id, session_data in self.active_sessions.items():
            last_activity = session_data.get("last_activity", session_data.get("started_at"))
            if last_activity:
                last_time = datetime.fromisoformat(last_activity)
                if current_time - last_time > timedelta(hours=2):  # 2 hour timeout
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
    
    async def analyze_conversation_sentiment(
        self, 
        user_message: str, 
        agent_response: str
    ) -> Dict[str, Any]:
        """Analyze sentiment and conversation quality"""
        
        # Simple keyword-based sentiment analysis
        positive_words = ["thank", "great", "excellent", "helpful", "good", "amazing", "perfect"]
        negative_words = ["bad", "terrible", "wrong", "frustrated", "angry", "disappointed", "useless"]
        question_words = ["how", "what", "when", "where", "why", "can", "could", "would"]
        
        user_text = user_message.lower()
        
        sentiment = "neutral"
        confidence = 0.5
        
        positive_count = sum(1 for word in positive_words if word in user_text)
        negative_count = sum(1 for word in negative_words if word in user_text)
        question_count = sum(1 for word in question_words if word in user_text)
        
        if positive_count > negative_count:
            sentiment = "positive"
            confidence = min(0.9, 0.5 + (positive_count * 0.1))
        elif negative_count > positive_count:
            sentiment = "negative" 
            confidence = min(0.9, 0.5 + (negative_count * 0.1))
        
        conversation_type = "question" if question_count > 0 else "statement"
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "conversation_type": conversation_type,
            "indicators": {
                "positive_signals": positive_count,
                "negative_signals": negative_count,
                "question_signals": question_count
            }
        }
    
    async def generate_conversation_summary(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Generate summary of conversation session"""
        
        # Get conversation history
        history = await self.get_conversation_history(user_id, session_id)
        
        if not history:
            return {"summary": "No conversation history found"}
        
        # Extract key topics and actions
        topics: set[str] = set()
        actions_discussed: List[str] = []
        user_concerns: List[str] = []
        
        for turn in history:
            user_msg = turn["user_message"].lower()
            agent_resp = turn["agent_response"].lower()
            
            # Extract topics
            if "tax" in user_msg or "tax" in agent_resp:
                topics.add("Tax Planning")
            if "investment" in user_msg or "investment" in agent_resp:
                topics.add("Investment Advice")
            if "cash flow" in user_msg or "cash flow" in agent_resp:
                topics.add("Cash Flow Management")
            if "business" in user_msg or "business" in agent_resp:
                topics.add("Business Strategy")
            
            # Extract actions
            if "automate" in agent_resp or "set up" in agent_resp:
                actions_discussed.append("Automation setup")
            if "recommend" in agent_resp or "suggest" in agent_resp:
                actions_discussed.append("Recommendations provided")
        
        return {
            "session_id": session_id,
            "user_id": user_id,
            "conversation_count": len(history),
            "topics_discussed": list(topics),
            "actions_discussed": actions_discussed,
            "user_concerns": user_concerns,
            "session_duration": self._calculate_session_duration(history),
            "summary": f"Discussed {len(topics)} main topics with {len(actions_discussed)} actionable recommendations."
        }
    
    def _calculate_session_duration(self, history: List[Dict[str, Any]]) -> str:
        """Calculate session duration from conversation history"""
        if len(history) < 2:
            return "< 1 minute"
        
        try:
            start_time = datetime.fromisoformat(history[-1]["timestamp"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(history[0]["timestamp"].replace('Z', '+00:00'))
            duration = end_time - start_time
            
            minutes = int(duration.total_seconds() / 60)
            if minutes < 1:
                return "< 1 minute"
            elif minutes < 60:
                return f"{minutes} minutes"
            else:
                hours = minutes // 60
                mins = minutes % 60
                return f"{hours}h {mins}m"
                
        except Exception:
            return "Unknown duration"
    
    async def get_conversation_recommendations(
        self,
        user_id: str,
        current_context: Dict[str, Any]
    ) -> List[str]:
        """Generate conversation recommendations based on context"""
        
        recommendations: List[str] = []
        
        financial_context = current_context.get("financial_context", {})
        
        # Financial health recommendations
        current_balance = financial_context.get("current_balance", 0)
        if current_balance < 2000:
            recommendations.append("Let's review your cash flow and identify ways to improve it")
        
        # Tax-related recommendations
        tax_due = financial_context.get("tax_due", 0)
        if tax_due > 1000:
            recommendations.append("I can help optimize your tax strategy and find potential savings")
        
        # Business growth recommendations
        monthly_profit = financial_context.get("monthly_profit", 0)
        if monthly_profit > 1000:
            recommendations.append("With your current profit levels, let's explore growth opportunities")
        
        # General recommendations
        recommendations.extend([
            "Would you like me to analyze your recent financial performance?",
            "I can set up automated reminders for important financial deadlines",
            "Let me show you personalized insights about your business"
        ])
        
        return recommendations[:4]  # Return top 4 recommendations
    
    async def handle_conversation_error(
        self,
        user_id: str,
        session_id: str,
        error_message: str,
        user_message: str
    ) -> Dict[str, Any]:
        """Handle conversation errors gracefully"""
        
        # Log error for debugging
        error_data = {
            "user_id": user_id,
            "session_id": session_id,
            "error_message": error_message,
            "user_message": user_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Store error for analysis
        await self.memory_manager.store_conversation(  # type: ignore
            user_id=user_id,
            user_message=user_message,
            agent_response=f"[ERROR] {error_message}",
            metadata={"error": True, "error_details": error_data}
        )
        
        # Generate helpful error response
        return {
            "response": "I apologize, but I'm experiencing a technical difficulty. Let me try a different approach to help you with that.",
            "suggestions": [
                "Try rephrasing your question",
                "Ask about a different topic",
                "Contact human support if this persists",
                "Let me show you what I can help with"
            ],
            "error_logged": True
        }
    
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get metrics for a specific session"""
        
        session_data = self.active_sessions.get(session_id, {})
        
        if not session_data:
            return {"error": "Session not found"}
        
        return {
            "session_id": session_id,
            "user_id": session_data.get("user_id"),
            "started_at": session_data.get("started_at"),
            "turn_count": session_data.get("turn_count", 0),
            "last_activity": session_data.get("last_activity"),
            "is_active": True,  # If it's in active_sessions, it's active
            "estimated_satisfaction": 4.2  # Placeholder - would calculate from sentiment
        }