import os
from typing import Annotated, List, Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from .agent.selfmate_agent import SelfMateAgent
from .agent.conversation_manager import ConversationManager
from .memory.memory_manager import MemoryManager
from .tools.tool_registry import ToolRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    global agent_instance, conversation_manager, memory_manager, tool_registry
    
    # Initialize Memory Manager
    memory_manager = MemoryManager(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/8"),
        vector_db_url=os.getenv("WEAVIATE_URL", "http://weaviate:8080")
    )
    await memory_manager.initialize()
    
    # Initialize Tool Registry
    tool_registry = ToolRegistry()
    await tool_registry.discover_services()
    
    # Initialize Conversation Manager
    conversation_manager = ConversationManager(memory_manager)
    
    # Initialize Main Agent
    agent_instance = SelfMateAgent(
        memory_manager=memory_manager,
        tool_registry=tool_registry,
        openai_api_key=os.getenv("OPENAI_API_KEY", "default_key"),
        model="gpt-4-turbo-preview"
    )
    
    print("🤖 SelfMate AI Agent initialized successfully!")
    
    yield
    
    # Shutdown
    if memory_manager:
        await memory_manager.close()  # type: ignore
    print("🤖 SelfMate AI Agent shutdown completed.")

app = FastAPI(
    title="AI Agent Service - SelfMate",
    description="Autonomous AI Financial Advisor for SelfMonitor platform.",
    version="1.0.0",
    lifespan=lifespan
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
class MessageType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class ConversationMessage(BaseModel):
    message_id: str
    user_id: str
    session_id: str
    message_type: MessageType
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    message_id: str
    actions_taken: List[str]
    recommendations: List[str]
    confidence_score: float
    processing_time_ms: int

class AgentCapability(BaseModel):
    capability_name: str
    description: str
    confidence_level: float
    last_updated: datetime

class AgentStatus(BaseModel):
    status: str
    active_sessions: int
    total_conversations: int
    capabilities: List[AgentCapability]
    uptime_hours: float
    performance_metrics: Dict[str, float]

# --- Global Components ---
agent_instance: Optional[SelfMateAgent] = None
conversation_manager: Optional[ConversationManager] = None
memory_manager: Optional[MemoryManager] = None
tool_registry: Optional[ToolRegistry] = None



# --- Health Check ---
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-agent-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_ready": agent_instance is not None
    }

# --- Agent Status ---
@app.get("/status", response_model=AgentStatus)
async def get_agent_status(current_user: str = Depends(get_current_user_id)) -> AgentStatus:
    """Get comprehensive agent status"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return AgentStatus(
        status="active" if agent_instance.is_ready() else "initializing",
        active_sessions=conversation_manager.get_active_session_count() if conversation_manager else 0,
        total_conversations=await conversation_manager.get_total_conversation_count() if conversation_manager else 0,
        capabilities=[
            AgentCapability(
                capability_name="Financial Analysis",
                description="Real-time financial health assessment and recommendations",
                confidence_level=0.92,
                last_updated=datetime.now(timezone.utc)
            ),
            AgentCapability(
                capability_name="Tax Optimization",
                description="Automated tax planning and compliance assistance",
                confidence_level=0.88,
                last_updated=datetime.now(timezone.utc)
            ),
            AgentCapability(
                capability_name="Business Growth",
                description="Strategic business advice and market insights",
                confidence_level=0.85,
                last_updated=datetime.now(timezone.utc)
            ),
            AgentCapability(
                capability_name="Fraud Detection",
                description="Real-time transaction monitoring and alerts",
                confidence_level=0.94,
                last_updated=datetime.now(timezone.utc)
            ),
            AgentCapability(
                capability_name="Invoice Management",
                description="Automated invoice processing and follow-ups",
                confidence_level=0.91,
                last_updated=datetime.now(timezone.utc)
            )
        ],
        uptime_hours=agent_instance.get_uptime_hours(),
        performance_metrics={
            "avg_response_time_ms": 850.0,
            "success_rate": 0.987,
            "user_satisfaction": 4.8,
            "automation_rate": 0.76
        }
    )

# --- Chat Interface ---
@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user_id)
) -> ChatResponse:
    """Main chat interface with SelfMate Agent"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    start_time = datetime.now(timezone.utc)
    session_id = request.session_id or f"session_{current_user}_{int(datetime.now(timezone.utc).timestamp())}"
    
    # Get conversation context
    if conversation_manager is None:
        raise HTTPException(status_code=503, detail="Conversation manager not initialized")
        
    conversation_context = await conversation_manager.get_conversation_context(
        user_id=current_user,
        session_id=session_id
    )
    
    # Process message through AI Agent
    agent_response = await agent_instance.process_message(
        user_id=current_user,
        message=request.message,
        context={
            **conversation_context,
            **(request.context or {})
        }
    )
    
    # Save conversation
    message_id = f"msg_{current_user}_{int(datetime.now(timezone.utc).timestamp())}"
    await conversation_manager.save_conversation_turn(
        user_id=current_user,
        session_id=session_id,
        user_message=request.message,
        agent_response=agent_response.response,
        metadata={
            "actions_taken": agent_response.actions_taken,
            "confidence": agent_response.confidence_score
        }
    )
    
    # Schedule background tasks
    background_tasks.add_task(
        process_agent_insights,
        current_user,
        agent_response.insights
    )
    
    processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    
    return ChatResponse(
        response=agent_response.response,
        session_id=session_id,
        message_id=message_id,
        actions_taken=agent_response.actions_taken,
        recommendations=agent_response.recommendations,
        confidence_score=agent_response.confidence_score,
        processing_time_ms=processing_time
    )

# --- Conversation History ---
@app.get("/conversations/{session_id}")
async def get_conversation_history(
    session_id: str,
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Get conversation history for a session"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not initialized")
    
    history = await conversation_manager.get_conversation_history(
        user_id=current_user,
        session_id=session_id
    )
    
    return {
        "session_id": session_id,
        "user_id": current_user,
        "message_count": len(history),
        "messages": history
    }

# --- Proactive Insights ---
@app.get("/insights/proactive")
async def get_proactive_insights(
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Get proactive insights and alerts for user"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    insights = await agent_instance.generate_proactive_insights(user_id=current_user)
    
    return {
        "user_id": current_user,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "insights": insights,
        "next_check": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    }

# --- Agent Learning ---
@app.post("/feedback")
async def submit_feedback(
    message_id: str,
    rating: int = Field(..., ge=1, le=5),
    feedback: Optional[str] = None,
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    """Submit feedback for agent improvement"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    await agent_instance.process_feedback(
        user_id=current_user,
        message_id=message_id,
        rating=rating,
        feedback=feedback
    )
    
    return {
        "status": "feedback_received",
        "message": "Thank you for your feedback! SelfMate will learn from this."
    }

# --- Background Tasks ---
async def process_agent_insights(user_id: str, insights: List[Dict[str, Any]]):
    """Process and store agent insights in background"""
    if memory_manager:
        for insight in insights:
            await memory_manager.store_user_insight(user_id, insight)  # type: ignore

# --- Administrative Endpoints ---
@app.post("/admin/retrain")
async def trigger_agent_retraining(
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    """Trigger agent retraining (admin only)"""
    # TODO: Add admin role check
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Schedule retraining in background
    await agent_instance.schedule_retraining()
    
    return {
        "status": "retraining_scheduled",
        "message": "Agent retraining has been scheduled. This may take several hours."
    }

@app.get("/admin/metrics")
async def get_agent_metrics(
    current_user: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Get detailed agent performance metrics"""
    # TODO: Add admin role check
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    metrics = await agent_instance.get_performance_metrics()
    
    return {
        "collection_time": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)  # type: ignore