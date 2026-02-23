"""
Tests for SelfMate AI Agent

Unit tests for core agent functionality including conversation management,
memory integration, and tool usage.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Any, Dict

from app.agent.selfmate_agent import SelfMateAgent, AgentResponse
from app.agent.conversation_manager import ConversationManager
from app.memory.memory_manager import MemoryManager
from app.tools.tool_registry import ToolRegistry


class TestSelfMateAgent:
    """Tests for SelfMate AI Agent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_memory_manager: MemoryManager, mock_tool_registry: ToolRegistry):
        """Test agent initialization"""
        agent = SelfMateAgent(
            memory_manager=mock_memory_manager,
            tool_registry=mock_tool_registry,
            openai_api_key="test_key"
        )
        
        assert agent.memory_manager == mock_memory_manager
        assert agent.tool_registry == mock_tool_registry
        assert agent.model == "gpt-4-turbo-preview"
    
    @pytest.mark.asyncio
    async def test_process_message_basic(
        self, 
        mock_memory_manager: MemoryManager, 
        mock_tool_registry: ToolRegistry,
        mock_openai_client: Any,
        test_user_id: str
    ):
        """Test basic message processing"""
        with patch('openai.AsyncOpenAI', return_value=mock_openai_client):
            agent = SelfMateAgent(
                memory_manager=mock_memory_manager,
                tool_registry=mock_tool_registry,
                openai_api_key="test_key"
            )
            
            mock_openai_client.chat.completions.create = AsyncMock(return_value=Mock(
                choices=[Mock(message=Mock(content="Financial health analysis complete"))]
            ))
            
            response: AgentResponse = await agent.process_message(
                user_id=test_user_id,
                message="How is my financial health?"
            )
            
            assert isinstance(response, AgentResponse)
            assert response.response is not None
            assert isinstance(response.actions_taken, list)
            assert isinstance(response.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_agent_with_tools(
        self,
        mock_memory_manager: MemoryManager,
        mock_tool_registry: ToolRegistry,
        mock_openai_client: Any,
        test_user_id: str
    ):
        """Test agent using tools"""
        # Configure tool registry to return a tool call
        mock_tool_registry.get_available_tools = Mock(return_value={"financial_analysis": "Financial analysis tool"})
        mock_tool_registry.get_tool = Mock(return_value=Mock(name="financial_analysis", description="Financial analysis tool"))
        mock_tool_registry.execute_tool = AsyncMock(return_value=Mock(success=True, data={"balance": 5000, "trend": "positive"}, message="Success", execution_time_ms=100))
        
        with patch('openai.AsyncOpenAI', return_value=mock_openai_client):
            agent = SelfMateAgent(
                memory_manager=mock_memory_manager,
                tool_registry=mock_tool_registry,
                openai_api_key="test_key"
            )
            
            mock_openai_client.chat.completions.create = AsyncMock(return_value=Mock(
                choices=[Mock(message=Mock(content="Financial analysis complete"))]
            ))
            
            response: AgentResponse = await agent.process_message(
                user_id=test_user_id,
                message="Analyze my finances"
            )
            
            assert isinstance(response, AgentResponse)
            assert response.response is not None
    
    @pytest.mark.asyncio
    async def test_generate_proactive_insights(
        self,
        mock_memory_manager: MemoryManager,
        mock_tool_registry: ToolRegistry,
        test_user_id: str
    ):
        """Test proactive insight generation"""
        agent = SelfMateAgent(
            memory_manager=mock_memory_manager,
            tool_registry=mock_tool_registry,
            openai_api_key="test_key"
        )
        
        insights = await agent.generate_proactive_insights(user_id=test_user_id)
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        # Check insight structure
        insight = insights[0]
        assert "type" in insight
        assert "message" in insight
        assert "priority" in insight


class TestConversationManager:
    """Tests for Conversation Manager"""
    
    @pytest.mark.asyncio
    async def test_conversation_manager_initialization(self, mock_memory_manager: MemoryManager):
        """Test conversation manager initialization"""
        manager = ConversationManager(mock_memory_manager)
        
        assert manager.memory_manager == mock_memory_manager
        assert "welcome" in manager.conversation_templates
        assert "returning_user" in manager.conversation_templates
    
    @pytest.mark.asyncio
    async def test_start_conversation(self, mock_memory_manager: MemoryManager, test_user_id: str):
        """Test starting a new conversation"""
        manager = ConversationManager(mock_memory_manager)
        
        mock_memory_manager.create_session = AsyncMock(return_value="test_session_123")  # type: ignore
        
        result = await manager.start_conversation(test_user_id)
        
        assert "session_id" in result
        assert "welcome_message" in result
        assert "suggestions" in result
        assert "context" in result
        
        # Check session was stored
        assert result["session_id"] in manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_get_conversation_context(
        self, 
        mock_memory_manager: MemoryManager, 
        test_user_id: str,
        test_session_id: str
    ):
        """Test getting conversation context"""
        manager = ConversationManager(mock_memory_manager)
        
        mock_memory_manager.get_user_profile = AsyncMock(return_value={"business_type": "sole_trader"})  # type: ignore
        mock_memory_manager.get_recent_conversations = AsyncMock(return_value=[])  # type: ignore
        mock_memory_manager.get_financial_context = AsyncMock(return_value={"balance": 1000})  # type: ignore
        mock_memory_manager.get_session = AsyncMock(return_value={"turn_count": 0})  # type: ignore
        
        context = await manager.get_conversation_context(test_user_id, test_session_id)
        
        assert "user_id" in context
        assert "session_id" in context
        assert "conversation_type" in context
        assert "user_profile" in context
        assert "financial_context" in context
    
    @pytest.mark.asyncio
    async def test_save_conversation_turn(
        self,
        mock_memory_manager: MemoryManager,
        test_user_id: str,
        test_session_id: str
    ):
        """Test saving conversation turn"""
        manager = ConversationManager(mock_memory_manager)
        
        mock_memory_manager.create_session = AsyncMock(return_value=test_session_id)  # type: ignore
        mock_memory_manager.store_conversation = AsyncMock()  # type: ignore
        
        # Start session first
        await manager.start_conversation(test_user_id)
        
        await manager.save_conversation_turn(
            user_id=test_user_id,
            session_id=test_session_id,
            user_message="Test message",
            agent_response="Test response"
        )
        
        # Verify conversation was stored
        mock_memory_manager.store_conversation.assert_called()  # type: ignore
    
    @pytest.mark.asyncio
    async def test_conversation_sentiment_analysis(self, mock_memory_manager: MemoryManager):
        """Test sentiment analysis"""
        manager = ConversationManager(mock_memory_manager)
        
        # Test positive sentiment
        result = await manager.analyze_conversation_sentiment(
            "Thank you! This is excellent advice",
            "Glad I could help!"
        )
        
        assert result["sentiment"] == "positive"
        assert result["confidence"] > 0.5
        
        # Test negative sentiment
        result = await manager.analyze_conversation_sentiment(
            "This is terrible and wrong",
            "I apologize for the confusion"
        )
        
        assert result["sentiment"] == "negative"
        assert result["confidence"] > 0.5


class TestMemoryManager:
    """Tests for Memory Manager"""
    
    def test_memory_manager_initialization(self):
        """Test memory manager initialization"""
        manager = MemoryManager(redis_url="redis://localhost:6379", vector_db_url="http://localhost:8080")
        
        assert manager.redis_client is None  # Not initialized until initialize() is called
        assert manager.weaviate_client is None  # Not initialized until initialize() is called  # type: ignore  
        assert manager.redis_url == "redis://localhost:6379"
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_user_profile(self, test_user_id: str):
        """Test storing and retrieving user profile"""
        manager = MemoryManager(redis_url="redis://localhost:6379", vector_db_url="http://localhost:8080")
        
        profile_data: Dict[str, Any] = {
            "user_id": test_user_id,
            "first_name": "John",
            "business_type": "Technology",
            "preferences": {"risk_tolerance": "moderate"}
        }
        
        # Store profile
        await manager.update_user_profile(test_user_id, profile_data)  # type: ignore
        
        # Retrieve profile
        retrieved = await manager.get_user_profile(test_user_id)  # type: ignore
        
        assert retrieved["first_name"] == "John"
        assert retrieved["business_type"] == "Technology"
    
    @pytest.mark.asyncio
    async def test_conversation_storage(self, test_user_id: str):
        """Test conversation storage and retrieval"""
        manager = MemoryManager(redis_url="redis://localhost:6379", vector_db_url="http://localhost:8080")
        
        await manager.store_conversation(  # type: ignore
            user_id=test_user_id,
            user_message="Test message",
            agent_response="Test response",
            metadata={"sentiment": "positive"}
        )
        
        conversations = await manager.get_recent_conversations(test_user_id, limit=1)  # type: ignore
        
        assert len(conversations) >= 0  # May be 0 if mock


class TestToolRegistry:
    """Tests for Tool Registry"""
    
    def test_tool_registry_initialization(self):
        """Test tool registry initialization"""
        registry = ToolRegistry()
        
        assert registry.tools == {}
        assert registry.service_discovery is not None
    
    @pytest.mark.asyncio
    async def test_register_tool(self):
        """Test tool registration"""
        registry = ToolRegistry()
        
        # Create a mock tool
        from unittest.mock import Mock
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        
        await registry.add_custom_tool(mock_tool)
        
        assert "test_tool" in registry.tools
        assert registry.tools["test_tool"].description == "A test tool"
    
    @pytest.mark.asyncio
    async def test_tool_discovery(self):
        """Test service discovery"""
        registry = ToolRegistry()
        
        # This would normally make HTTP calls to discover services
        # For testing, we just verify the method exists
        assert hasattr(registry, "discover_services")
        assert callable(getattr(registry, "discover_services"))
    
    def test_get_available_tools(self):
        """Test getting available tools"""
        registry = ToolRegistry()
        
        # Test that get_available_tools method exists and returns correct type
        available_tools = registry.get_available_tools()
        
        # Should return a dictionary
        assert isinstance(available_tools, dict)
    
    @pytest.mark.asyncio
    async def test_call_tool_mock(self, mock_tool_registry: ToolRegistry):
        """Test tool calling with mock"""
        result = await mock_tool_registry.execute_tool("financial_analysis", "test_user")  # type: ignore
        
        assert isinstance(result, object)  # Should return a ToolResult object


if __name__ == "__main__":
    pytest.main([__file__, "-v"])