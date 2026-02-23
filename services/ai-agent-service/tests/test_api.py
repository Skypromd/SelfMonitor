"""
API Integration Tests for AI Agent Service

Tests for FastAPI endpoints including chat, sessions, health checks, and admin endpoints.
"""

import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
import httpx
from unittest.mock import patch, Mock

from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Mock authentication headers"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_agent():
    """Mock AI agent for testing"""
    mock_agent = Mock()
    mock_agent.process_message.return_value = {
        "response": "Test response from AI agent",
        "session_id": "test_session_123",
        "metadata": {
            "confidence": 0.95,
            "response_time_ms": 150,
            "tools_used": []
        }
    }
    mock_agent.generate_proactive_insights.return_value = [
        {
            "type": "opportunity",
            "title": "Investment Opportunity",
            "description": "Consider investing in index funds",
            "priority": "medium",
            "estimated_impact": "£500/month"
        }
    ]
    return mock_agent


@pytest.fixture
def mock_conversation_manager():
    """Mock conversation manager for testing"""
    mock_manager = Mock()
    mock_manager.start_conversation.return_value = {
        "session_id": "test_session_123",
        "welcome_message": "Hello! I'm SelfMate, your AI financial advisor.",
        "suggestions": ["Analyze my finances", "Help with taxes"],
        "context": {}
    }
    mock_manager.get_conversation_history.return_value = [
        {
            "timestamp": "2026-02-20T10:00:00Z",
            "user_message": "How's my cash flow?",
            "agent_response": "Your cash flow is healthy!",
            "metadata": {}
        }
    ]
    mock_manager.get_active_session_count.return_value = 5
    mock_manager.get_session_metrics.return_value = {
        "session_id": "test_session_123",
        "user_id": "test_user",
        "turn_count": 3,
        "is_active": True
    }
    return mock_manager


class TestChatEndpoints:
    """Tests for chat-related endpoints"""
    
    def test_chat_endpoint_success(self, client: TestClient, auth_headers: Dict[str, str], mock_agent: Mock):
        """Test successful chat interaction"""
        with patch('app.main.agent', mock_agent):
            response = client.post(  # type: ignore
                "/chat",
                json={
                    "message": "How is my financial health?",
                    "session_id": "test_session_123"
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "response" in data
            assert "session_id" in data
            assert "metadata" in data
            assert data["session_id"] == "test_session_123"
    
    def test_chat_endpoint_without_session(self, client: TestClient, auth_headers: Dict[str, str], mock_agent: Mock):
        """Test chat without existing session"""
        with patch('app.main.agent', mock_agent):
            response = client.post(  # type: ignore
                "/chat",
                json={"message": "Hello"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
    
    def test_chat_endpoint_invalid_request(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test chat with invalid request"""
        response = client.post(  # type: ignore
            "/chat",
            json={},  # Missing required "message" field
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_endpoint_unauthorized(self, client: TestClient):
        """Test chat without authentication"""
        response = client.post(  # type: ignore
            "/chat",
            json={"message": "Hello"}
            # No auth headers
        )
        
        assert response.status_code == 401
    
    def test_chat_stream_endpoint(self, client: TestClient, auth_headers: Dict[str, str], mock_agent: Mock):
        """Test streaming chat endpoint"""
        with patch('app.main.agent', mock_agent):
            response = client.post(  # type: ignore
                "/chat/stream",
                json={"message": "Tell me about my finances"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestSessionEndpoints:
    """Tests for session management endpoints"""
    
    def test_create_session(self, client: TestClient, auth_headers: Dict[str, str], mock_conversation_manager: Mock):
        """Test creating new session"""
        with patch('app.main.conversation_manager', mock_conversation_manager):
            response = client.post(  # type: ignore
                "/sessions",
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            
            assert "session_id" in data
            assert "welcome_message" in data
            assert "suggestions" in data
    
    def test_get_sessions(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting user sessions"""
        response = client.get(  # type: ignore
            "/sessions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sessions" in data
        assert "total" in data
        assert isinstance(data["sessions"], list)
    
    def test_get_session_details(self, client: TestClient, auth_headers: Dict[str, str], mock_conversation_manager: Mock):
        """Test getting specific session details"""
        with patch('app.main.conversation_manager', mock_conversation_manager):
            response = client.get(  # type: ignore
                "/sessions/test_session_123",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "session_id" in data
            assert "is_active" in data
    
    def test_get_session_not_found(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting non-existent session"""
        response = client.get(  # type: ignore
            "/sessions/nonexistent_session",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_end_session(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test ending a session"""
        response = client.delete(  # type: ignore
            "/sessions/test_session_123",
            headers=auth_headers
        )
        
        # Should succeed even if session doesn't exist (idempotent)
        assert response.status_code in [200, 404]
    
    def test_get_conversation_history(self, client: TestClient, auth_headers: Dict[str, str], mock_conversation_manager: Mock):
        """Test getting conversation history"""
        with patch('app.main.conversation_manager', mock_conversation_manager):
            response = client.get(  # type: ignore
                "/sessions/test_session_123/history",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "conversations" in data
            assert isinstance(data["conversations"], list)
    
    def test_get_conversation_history_with_limit(self, client: TestClient, auth_headers: Dict[str, str], mock_conversation_manager: Mock):
        """Test getting conversation history with limit"""
        with patch('app.main.conversation_manager', mock_conversation_manager):
            response = client.get(  # type: ignore
                "/sessions/test_session_123/history?limit=10",
                headers=auth_headers
            )
            
            assert response.status_code == 200


class TestInsightsEndpoints:
    """Tests for insights endpoints"""
    
    def test_get_insights(self, client: TestClient, auth_headers: Dict[str, str], mock_agent: Mock):
        """Test getting proactive insights"""
        with patch('app.main.agent', mock_agent):
            response = client.get(  # type: ignore
                "/insights",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "insights" in data
            assert "generated_at" in data
            assert isinstance(data["insights"], list)
            
            if data["insights"]:
                insight = data["insights"][0]
                assert "type" in insight
                assert "title" in insight
                assert "description" in insight


class TestHealthEndpoints:
    """Tests for health and monitoring endpoints"""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")  # type: ignore
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "dependencies" in data
        
        # Check dependencies structure
        deps = data["dependencies"]
        assert "database" in deps
        assert "ai_service" in deps
        assert "memory_system" in deps
    
    def test_metrics_endpoint(self, client: TestClient, mock_conversation_manager: Mock):
        """Test metrics endpoint"""
        with patch('app.main.conversation_manager', mock_conversation_manager):
            response = client.get("/metrics")  # type: ignore
            
            assert response.status_code == 200
            data = response.json()
            
            assert "requests_total" in data
            assert "active_sessions" in data
            assert "average_response_time_ms" in data
            assert "memory_usage_bytes" in data


class TestAdminEndpoints:
    """Tests for admin endpoints"""
    
    def test_admin_stats(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test admin statistics endpoint"""
        response = client.get(  # type: ignore
            "/admin/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_conversations" in data
        assert "total_users" in data
        assert "performance_metrics" in data
    
    def test_admin_stats_unauthorized(self, client: TestClient):
        """Test admin stats without authentication"""
        response = client.get("/admin/stats")  # type: ignore
        
        assert response.status_code == 401


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_internal_server_error_handling(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test handling of internal server errors"""
        # Simulate an error by patching a service to raise an exception
        with patch('app.main.agent') as mock_agent:
            mock_agent.process_message.side_effect = Exception("Test error")
            
            response = client.post(  # type: ignore
                "/chat",
                json={"message": "Test message"},
                headers=auth_headers
            )
            
            # Should handle gracefully and return 500
            assert response.status_code == 500
            data = response.json()
            assert "error" in data
    
    def test_validation_errors(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test request validation errors"""
        # Test with invalid message type
        response = client.post(  # type: ignore
            "/chat",
            json={"message": 123},  # Should be string
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_rate_limiting(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test rate limiting (if implemented)"""
        # Make multiple rapid requests
        responses: list[httpx.Response] = []
        for i in range(5):
            response = client.post(  # type: ignore
                "/chat",
                json={"message": f"Message {i}"},
                headers=auth_headers
            )
            responses.append(response)  # type: ignore
        
        # All should succeed for this test (rate limiting not strictly implemented yet)
        # but structure is ready for it
        assert all(r.status_code in [200, 429] for r in responses)  # type: ignore


class TestRequestResponseFlow:
    """Integration tests for complete request/response flows"""
    
    def test_complete_conversation_flow(self, client: TestClient, auth_headers: Dict[str, str], mock_agent: Mock, mock_conversation_manager: Mock):
        """Test complete conversation flow"""
        with patch('app.main.agent', mock_agent), patch('app.main.conversation_manager', mock_conversation_manager):
            # 1. Create session
            session_response = client.post("/sessions", headers=auth_headers)  # type: ignore
            assert session_response.status_code == 201
            session_data = session_response.json()
            session_id = session_data["session_id"]
            
            # 2. Send message
            chat_response = client.post(  # type: ignore
                "/chat",
                json={
                    "message": "How's my financial health?",
                    "session_id": session_id
                },
                headers=auth_headers
            )
            assert chat_response.status_code == 200
            
            # 3. Get conversation history
            history_response = client.get(  # type: ignore
                f"/sessions/{session_id}/history",
                headers=auth_headers
            )
            assert history_response.status_code == 200
            
            # 4. End session
            end_response = client.delete(  # type: ignore
                f"/sessions/{session_id}",
                headers=auth_headers
            )
            assert end_response.status_code in [200, 404]
    
    def test_insights_flow(self, client: TestClient, auth_headers: Dict[str, str], mock_agent: Mock) -> None:
        """Test proactive insights flow"""
        with patch('app.main.agent', mock_agent):
            # Get insights without explicit conversation
            response: httpx.Response = client.get("/insights", headers=auth_headers)  # type: ignore
            
            assert response.status_code == 200
            data: Dict[str, Any] = response.json()  # type: ignore
            assert "insights" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])