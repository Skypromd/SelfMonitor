"""
Memory Manager for SelfMate AI Agent

Handles short-term and long-term memory, user context, and conversation history.
Integrates with Redis for fast access and Weaviate for semantic search.
"""

import json
from typing import Dict, List, Any, Optional, cast
from datetime import datetime, timezone
import hashlib

import redis.asyncio as redis

# Weaviate availability check
weaviate_available = False
weaviate: Any = None

try:
    import weaviate  # type: ignore
    weaviate_available = True
except ImportError:
    # Create stub for type checking
    pass


class MemoryManager:
    """
    Advanced memory management for SelfMate Agent
    
    Features:
    - Short-term memory (Redis) for immediate context
    - Long-term memory (Weaviate) for semantic search
    - User profile management
    - Conversation history
    - Financial context caching
    - Learning from interactions
    """
    
    def __init__(self, redis_url: str, vector_db_url: str):
        self.redis_url = redis_url
        self.vector_db_url = vector_db_url
        self.redis_client: Optional[redis.Redis] = None
        self.weaviate_client: Optional[Any] = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize memory systems"""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(self.redis_url)  # type: ignore
            await self.redis_client.ping()  # type: ignore
            
            # Initialize Weaviate connection if available
            if weaviate_available:
                self.weaviate_client = weaviate.Client(
                    url=self.vector_db_url,
                    additional_headers={"X-OpenAI-Api-Key": ""}  # Will be set in production
                )
                
                # Create schemas if they don't exist
                await self._create_weaviate_schemas()
            
            self.initialized = True
            print("🧠 Memory Manager initialized successfully!")
            
        except Exception as e:
            print(f"❌ Memory Manager initialization failed: {e}")
            raise
    
    async def _create_weaviate_schemas(self):
        """Create Weaviate schemas for different data types"""
        if not weaviate_available or self.weaviate_client is None:
            return
        
        # User Profile Schema
        user_profile_schema: Dict[str, Any] = {
            "class": "UserProfile",
            "description": "User profile and preferences for SelfMate Agent",
            "properties": [
                {
                    "name": "userId",
                    "dataType": ["string"],
                    "description": "Unique user identifier"
                },
                {
                    "name": "businessType", 
                    "dataType": ["string"],
                    "description": "Type of business or profession"
                },
                {
                    "name": "preferences",
                    "dataType": ["text"],
                    "description": "User preferences and communication style"
                },
                {
                    "name": "financialGoals",
                    "dataType": ["text"],
                    "description": "User's financial goals and objectives"
                },
                {
                    "name": "riskProfile",
                    "dataType": ["string"],
                    "description": "Risk tolerance profile"
                }
            ]
        }
        
        # Conversation Memory Schema
        conversation_schema: Dict[str, Any] = {
            "class": "ConversationMemory",
            "description": "Semantic memory of important conversation topics", 
            "properties": [
                {
                    "name": "userId",
                    "dataType": ["string"],
                    "description": "User ID"
                },
                {
                    "name": "content",
                    "dataType": ["text"], 
                    "description": "Conversation content"
                },
                {
                    "name": "topic",
                    "dataType": ["string"],
                    "description": "Main topic or category"
                },
                {
                    "name": "timestamp",
                    "dataType": ["date"],
                    "description": "When the conversation occurred"
                },
                {
                    "name": "importance",
                    "dataType": ["number"],
                    "description": "Importance score (0-1)"
                }
            ]
        }
        
        # Financial Insights Schema
        insights_schema: Dict[str, Any] = {
            "class": "FinancialInsight", 
            "description": "Financial insights and recommendations",
            "properties": [
                {
                    "name": "userId",
                    "dataType": ["string"],
                    "description": "User ID"
                },
                {
                    "name": "insightType",
                    "dataType": ["string"],
                    "description": "Type of insight (tax, growth, risk, etc.)"
                },
                {
                    "name": "description",
                    "dataType": ["text"],
                    "description": "Detailed description of the insight"
                },
                {
                    "name": "impact",
                    "dataType": ["text"],
                    "description": "Potential financial impact"
                },
                {
                    "name": "actionRequired",
                    "dataType": ["text"],
                    "description": "Recommended actions"
                },
                {
                    "name": "confidence",
                    "dataType": ["number"],
                    "description": "Confidence score (0-1)"
                }
            ]
        }
        
        try:
            # Create schemas (will skip if they exist)
            if self.weaviate_client is not None:
                if not self.weaviate_client.schema.contains(user_profile_schema):
                    self.weaviate_client.schema.create_class(user_profile_schema)
                
                if not self.weaviate_client.schema.contains(conversation_schema):
                    self.weaviate_client.schema.create_class(conversation_schema)
                
                if not self.weaviate_client.schema.contains(insights_schema):
                    self.weaviate_client.schema.create_class(insights_schema)
                    
                print("📊 Weaviate schemas created/verified successfully")
            
        except Exception as e:
            print(f"⚠️ Schema creation warning: {e}")
    
    # --- User Profile Management ---
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user profile"""
        if not self.redis_client:
            return {}
            
        try:
            # Try Redis cache first
            cached_profile = cast(Optional[str], await self.redis_client.get(f"profile:{user_id}"))  # type: ignore
            if cached_profile:
                return json.loads(cached_profile)
            
            # Fallback to default profile
            default_profile: Dict[str, Any] = {
                "user_id": user_id,
                "business_type": "Self-employed",
                "annual_revenue": 50000,
                "concerns": ["tax_optimization", "cash_flow"],
                "preferences": {
                    "communication_style": "professional",
                    "risk_tolerance": "moderate",
                    "goals": ["grow_revenue", "optimize_taxes"]
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Cache for 24 hours
            await self.redis_client.setex(  # type: ignore
                f"profile:{user_id}",
                86400,
                json.dumps(default_profile)
            )
            
            return default_profile
            
        except Exception as e:
            print(f"❌ Error getting user profile: {e}")
            return {"user_id": user_id}
    
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]):
        """Update user profile"""
        if not self.redis_client:
            return
            
        try:
            profile_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Update Redis cache
            await self.redis_client.setex(  # type: ignore
                f"profile:{user_id}",
                86400,
                json.dumps(profile_data)
            )
            
            # Store in long-term memory (Weaviate)
            if self.weaviate_client:
                self.weaviate_client.data_object.create(
                    data_object={
                        "userId": user_id,
                        "businessType": profile_data.get("business_type", ""),
                        "preferences": json.dumps(profile_data.get("preferences", {})),
                        "financialGoals": json.dumps(profile_data.get("goals", [])),
                        "riskProfile": profile_data.get("risk_tolerance", "moderate")
                    },
                    class_name="UserProfile",
                    uuid=self._generate_uuid(f"profile_{user_id}")
                )
                
        except Exception as e:
            print(f"❌ Error updating user profile: {e}")
    
    # --- Financial Context ---
    
    async def get_financial_context(self, user_id: str) -> Dict[str, Any]:
        """Get user's current financial context"""
        if not self.redis_client:
            return {}
            
        try:
            # Try cache first
            cached_context = cast(Optional[str], await self.redis_client.get(f"financial:{user_id}"))  # type: ignore
            if cached_context:
                return json.loads(cached_context)
            
            # Mock financial context (in production, would fetch from financial services)
            financial_context: Dict[str, Any] = {
                "user_id": user_id,
                "current_balance": 12500.00,
                "monthly_revenue": 8500.00,
                "monthly_expenses": 6200.00, 
                "monthly_profit": 2300.00,
                "tax_due": 3400.00,
                "outstanding_invoices": 15600.00,
                "metrics": {
                    "profit_margin": 0.27,
                    "cash_conversion_cycle": 45,
                    "debt_to_revenue_ratio": 0.12
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Cache for 1 hour (financial data changes frequently)
            await self.redis_client.setex(  # type: ignore
                f"financial:{user_id}",
                3600,
                json.dumps(financial_context)
            )
            
            return financial_context
            
        except Exception as e:
            print(f"❌ Error getting financial context: {e}")
            return {}
    
    async def update_financial_context(self, user_id: str, context: Dict[str, Any]):
        """Update financial context"""
        if not self.redis_client:
            return
            
        try:
            context["last_updated"] = datetime.now(timezone.utc).isoformat()
            await self.redis_client.setex(  # type: ignore
                f"financial:{user_id}",
                3600,  # 1 hour cache
                json.dumps(context)
            )
        except Exception as e:
            print(f"❌ Error updating financial context: {e}")
    
    # --- Conversation Management ---
    
    async def get_recent_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        if not self.redis_client:
            return []
            
        try:
            conversations_result = await self.redis_client.lrange(  # type: ignore
                f"conversations:{user_id}",
                0,
                limit - 1
            )
            conversations = cast(List[str], conversations_result)
            
            return [json.loads(conv) for conv in conversations]
            
        except Exception as e:
            print(f"❌ Error getting conversations: {e}")
            return []
    
    async def store_conversation(
        self, 
        user_id: str, 
        user_message: str, 
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Store conversation in memory"""
        if not self.redis_client:
            return
            
        try:
            conversation: Dict[str, Any] = {
                "user_id": user_id,
                "user_message": user_message,
                "agent_response": agent_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {}
            }
            
            # Store in Redis (keep last 50 conversations)
            self.redis_client.lpush(  # type: ignore
                f"conversations:{user_id}", 
                json.dumps(conversation)
            )
            self.redis_client.ltrim(f"conversations:{user_id}", 0, 49)  # type: ignore
            
            # Store important conversations in Weaviate for semantic search
            if self._is_important_conversation(user_message, agent_response):
                await self._store_semantic_memory(user_id, conversation)
                
        except Exception as e:
            print(f"❌ Error storing conversation: {e}")
    
    def _is_important_conversation(self, user_message: str, agent_response: str) -> bool:
        """Determine if conversation should be stored in long-term semantic memory"""
        important_keywords = [
            "tax", "investment", "business plan", "goal", "strategy",
            "concern", "problem", "opportunity", "decision", "advice"
        ]
        
        combined_text = f"{user_message} {agent_response}".lower()
        return any(keyword in combined_text for keyword in important_keywords)
    
    async def _store_semantic_memory(self, user_id: str, conversation: Dict[str, Any]):
        """Store conversation in Weaviate for semantic search"""
        if not self.weaviate_client:
            return
            
        try:
            # Extract topic from conversation
            topic = self._extract_conversation_topic(
                conversation["user_message"], 
                conversation["agent_response"]
            )
            
            self.weaviate_client.data_object.create(
                data_object={
                    "userId": user_id,
                    "content": f"{conversation['user_message']} {conversation['agent_response']}",
                    "topic": topic,
                    "timestamp": conversation["timestamp"],
                    "importance": 0.8  # High importance for stored conversations
                },
                class_name="ConversationMemory",
                uuid=self._generate_uuid(f"conv_{user_id}_{conversation['timestamp']}")
            )
            
        except Exception as e:
            print(f"❌ Error storing semantic memory: {e}")
    
    def _extract_conversation_topic(self, user_message: str, agent_response: str) -> str:
        """Extract main topic from conversation"""
        # Simple keyword-based topic extraction
        topics = {
            "tax": ["tax", "hmrc", "allowance", "deduction", "vat"],
            "investment": ["invest", "portfolio", "pension", "savings"],
            "business_growth": ["growth", "expand", "marketing", "revenue"],
            "cash_flow": ["cash", "flow", "payment", "invoice", "income"],
            "compliance": ["compliance", "regulation", "legal", "requirement"]
        }
        
        combined_text = f"{user_message} {agent_response}".lower()
        
        for topic, keywords in topics.items():
            if any(keyword in combined_text for keyword in keywords):
                return topic
                
        return "general"
    
    # --- Insights Management ---
    
    async def store_user_insight(self, user_id: str, insight: Dict[str, Any]):
        """Store user insights for future reference"""
        if not self.weaviate_client:
            return
            
        try:
            self.weaviate_client.data_object.create(
                data_object={
                    "userId": user_id,
                    "insightType": insight.get("type", "general"),
                    "description": insight.get("description", ""),
                    "impact": insight.get("impact", ""),
                    "actionRequired": insight.get("action_required", ""),
                    "confidence": insight.get("confidence", 0.5)
                },
                class_name="FinancialInsight",
                uuid=self._generate_uuid(f"insight_{user_id}_{datetime.now(timezone.utc).timestamp()}")
            )
            
        except Exception as e:
            print(f"❌ Error storing insight: {e}")
    
    async def get_similar_insights(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar insights using semantic search"""
        if not self.weaviate_client:
            return []
            
        try:
            result = (
                self.weaviate_client.query
                .get("FinancialInsight", ["description", "impact", "actionRequired", "confidence"])
                .with_near_text({"concepts": [query]})
                .with_where({
                    "path": ["userId"],
                    "operator": "Equal", 
                    "valueString": user_id
                })
                .with_limit(limit)
                .do()
            )
            
            insights = result.get("data", {}).get("Get", {}).get("FinancialInsight", [])
            return insights
            
        except Exception as e:
            print(f"❌ Error getting similar insights: {e}")
            return []
    
    # --- Feedback Management ---
    
    async def store_feedback(self, feedback_data: Dict[str, Any]):
        """Store user feedback for agent learning"""
        if not self.redis_client:
            return
            
        try:
            self.redis_client.lpush(  # type: ignore
                "agent_feedback",
                json.dumps(feedback_data)
            )
            
        except Exception as e:
            print(f"❌ Error storing feedback: {e}")
    
    # --- Session Management ---
    
    async def create_session(self, user_id: str) -> str:
        """Create new conversation session"""
        session_id = f"session_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        if self.redis_client:
            await self.redis_client.setex(  # type: ignore
                f"session:{session_id}",
                3600,  # 1 hour session
                json.dumps({
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_activity": datetime.now(timezone.utc).isoformat()
                })
            )
            
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        if not self.redis_client:
            return None
            
        try:
            session_data = await self.redis_client.get(f"session:{session_id}")  # type: ignore
            return json.loads(session_data) if session_data else None  # type: ignore
            
        except Exception as e:
            print(f"❌ Error getting session: {e}")
            return None
    
    # --- Utility Methods ---
    
    def _generate_uuid(self, input_string: str) -> str:
        """Generate consistent UUID from string"""
        return hashlib.md5(input_string.encode()).hexdigest()
    
    async def clear_user_cache(self, user_id: str):
        """Clear user's cached data"""
        if not self.redis_client:
            return
            
        try:
            patterns = [
                f"profile:{user_id}",
                f"financial:{user_id}",
                f"conversations:{user_id}",
                f"session:*{user_id}*"
            ]
            
            for pattern in patterns:
                keys = await self.redis_client.keys(pattern)  # type: ignore
                if keys:
                    await self.redis_client.delete(*keys)  # type: ignore
                    
        except Exception as e:
            print(f"❌ Error clearing cache: {e}")
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        stats = {
            "redis_connected": self.redis_client is not None,
            "weaviate_connected": self.weaviate_client is not None,
            "initialized": self.initialized
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info()  # type: ignore
                stats["redis_memory_usage"] = info.get("used_memory_human", "Unknown")  # type: ignore
                stats["redis_keyspace"] = len(await self.redis_client.keys("*"))  # type: ignore
            except Exception:
                pass
                
        return stats
    
    async def close(self):
        """Close memory connections"""
        if self.redis_client:
            await self.redis_client.close()  # type: ignore
        
        self.initialized = False
        print("🧠 Memory Manager closed")