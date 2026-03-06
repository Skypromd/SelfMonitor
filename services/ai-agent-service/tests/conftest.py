"""
Test configuration for AI Agent Service tests
"""

import os
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest

# Test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["REDIS_HOST"] = "localhost"
os.environ["WEAVIATE_URL"] = "http://localhost:8080"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key")


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = Mock()
    mock_client.chat.completions.create = AsyncMock(return_value=Mock(
        choices=[
            Mock(
                message=Mock(
                    content="Test response from AI agent"
                )
            )
        ]
    ))
    return mock_client


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager for testing"""
    mock_manager = Mock()
    # All async methods must use AsyncMock so they can be awaited
    mock_manager.get_user_profile = AsyncMock(return_value={
        "user_id": "test_user",
        "first_name": "John",
        "business_type": "Technology"
    })
    mock_manager.get_recent_conversations = AsyncMock(return_value=[])
    mock_manager.get_financial_context = AsyncMock(return_value={
        "current_balance": 5000,
        "monthly_profit": 2000
    })
    mock_manager.store_conversation = AsyncMock(return_value=True)
    mock_manager.create_session = AsyncMock(return_value="test_session_123")
    mock_manager.get_user_language = AsyncMock(return_value="en")
    mock_manager.get_session = AsyncMock(return_value={"turn_count": 0})
    mock_manager.update_session = AsyncMock()
    mock_manager.update_financial_context = AsyncMock()
    return mock_manager


@pytest.fixture
def mock_tool_registry():
    """Mock tool registry for testing"""
    mock_registry = Mock()
    # get_available_tools() returns a dict (tool_name → tool object) in the real implementation
    mock_registry.get_available_tools.return_value = {
        "financial_analysis": Mock(
            name="financial_analysis",
            description="Analyze financial data",
        )
    }
    mock_registry.call_tool = AsyncMock(return_value={"result": "test result"})
    # execute_tool is async and returns a ToolResult-like object
    mock_registry.execute_tool = AsyncMock(return_value=Mock(
        success=True,
        data={"balance": 5000, "trend": "positive"},
        message="Success",
        execution_time_ms=100,
    ))
    return mock_registry


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return "test_user_123"


@pytest.fixture
def test_session_id():
    """Test session ID"""
    return "test_session_123"


@pytest.fixture
def sample_conversation_history() -> List[Dict[str, Any]]:
    """Sample conversation history for testing"""
    return [
        {
            "timestamp": "2026-02-20T10:00:00Z",
            "user_message": "What's my cash flow like?",
            "agent_response": "Your cash flow looks healthy this month!",
            "metadata": {}
        },
        {
            "timestamp": "2026-02-20T10:05:00Z",
            "user_message": "Can you help with tax planning?",
            "agent_response": "I'd be happy to help with tax planning!",
            "metadata": {}
        }
    ]
