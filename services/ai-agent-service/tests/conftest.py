"""
Test configuration for AI Agent Service tests
"""

import os
import pytest
from typing import List, Dict, Any
from unittest.mock import Mock

# Test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["REDIS_HOST"] = "localhost"
os.environ["WEAVIATE_URL"] = "http://localhost:8080"
os.environ["POSTGRES_HOST"] = "localhost"


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content="Test response from AI agent"
                )
            )
        ]
    )
    return mock_client


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager for testing"""
    mock_manager = Mock()
    mock_manager.get_user_profile.return_value = {
        "user_id": "test_user",
        "first_name": "John",
        "business_type": "Technology"
    }
    mock_manager.get_recent_conversations.return_value = []
    mock_manager.get_financial_context.return_value = {
        "current_balance": 5000,
        "monthly_profit": 2000
    }
    mock_manager.store_conversation.return_value = True
    mock_manager.create_session.return_value = "test_session_123"
    return mock_manager


@pytest.fixture
def mock_tool_registry():
    """Mock tool registry for testing"""
    mock_registry = Mock()
    mock_registry.get_available_tools.return_value = [
        {
            "name": "financial_analysis",
            "description": "Analyze financial data",
            "url": "http://localhost:8001/analyze"
        }
    ]
    mock_registry.call_tool.return_value = {"result": "test result"}
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