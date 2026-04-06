"""Integration tests for Purple Team GPT.

This module tests:
- Authentication flow
- Session lifecycle with auth
- WebSocket authentication
"""

import os
import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Set environment variables before any imports
os.environ["APP_SECRET_KEY"] = "integration-test-secret-key-must-be-32-chars"
os.environ["APP_DEBUG"] = "true"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = MagicMock()
    
    # Mock session
    mock_session = MagicMock()
    mock_session.id = "test-session-123"
    mock_session.target = "192.168.1.1"
    mock_session.scope = "Test scope"
    mock_session.status = MagicMock()
    mock_session.status.value = "pending"
    mock_session.created_at = datetime.now(timezone.utc)
    mock_session.started_at = None
    mock_session.completed_at = None
    mock_session.to_dict = MagicMock(return_value={
        "id": "test-session-123",
        "target": "192.168.1.1",
        "status": "pending"
    })
    
    orchestrator.create_session = MagicMock(return_value=mock_session)
    orchestrator.get_session = MagicMock(return_value=mock_session)
    orchestrator.list_sessions = MagicMock(return_value=[mock_session])
    orchestrator.start_session_background = MagicMock()
    orchestrator.pause_session = MagicMock(return_value=True)
    orchestrator.resume_session = MagicMock(return_value=True)
    orchestrator.stop_session = MagicMock(return_value=mock_session)
    orchestrator.delete_session = MagicMock(return_value=True)
    orchestrator.get_metrics = MagicMock(return_value={
        "session_id": "test-session-123",
        "target": "192.168.1.1",
        "scope": "Test scope",
        "status": "pending",
        "duration": "0:00:00",
        "red_agent": {"total_findings": 0, "total_steps": 0},
        "blue_agent": {"total_findings": 0, "total_steps": 0},
        "total_findings": 0,
        "total_events": 0,
    })
    orchestrator.get_all_metrics = MagicMock(return_value={})
    
    return orchestrator


# ============================================================================
# Authentication Flow Tests
# ============================================================================

class TestAuthenticationFlow:
    """Tests for the authentication flow."""
    
    @pytest.fixture
    def security_module(self):
        """Get security module with mocked settings."""
        from purple_team_gpt.backend import security
        security._rate_limiter = None
        yield security
    
    def test_create_token_endpoint(self, mock_orchestrator):
        """Test the token creation endpoint."""
        from purple_team_gpt.backend.main import app
        
        client = TestClient(app)
        
        # Request token
        response = client.post("/auth/token")
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_access_protected_endpoint_without_token(self):
        """Test that protected endpoints require authentication."""
        from purple_team_gpt.backend.main import app
        from purple_team_gpt.backend import security
        security._rate_limiter = None
        
        client = TestClient(app)
        
        # Try to access protected endpoint without token
        response = client.get("/status")
        
        assert response.status_code == 401
    
    def test_access_protected_endpoint_with_valid_token(self, mock_orchestrator):
        """Test accessing protected endpoint with valid token."""
        from purple_team_gpt.backend.main import app
        from purple_team_gpt.backend import security
        security._rate_limiter = None
        
        # Patch the global orchestrator
        import purple_team_gpt.backend.main as main_module
        main_module.orchestrator = mock_orchestrator
        main_module.llm_engine = MagicMock()
        main_module.vector_store = MagicMock()
        main_module.feedback_store = MagicMock()
        
        client = TestClient(app)
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Access protected endpoint with token
        response = client.get(
            "/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    def test_access_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid token."""
        from purple_team_gpt.backend.main import app
        from purple_team_gpt.backend import security
        security._rate_limiter = None
        
        client = TestClient(app)
        
        # Try to access with invalid token
        response = client.get(
            "/status",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_token_contains_user_info(self, security_module):
        """Test that token contains user information."""
        from purple_team_gpt.backend.security import create_access_token, verify_token
        
        # Create token with user data
        user_data = {
            "sub": "test_user",
            "roles": ["user", "admin"],
            "permissions": ["read", "write"]
        }
        token = create_access_token(user_data)
        
        # Verify and check contents
        payload = verify_token(token)
        
        assert payload["sub"] == "test_user"
        assert "user" in payload["roles"]
        assert "admin" in payload["roles"]
        assert "read" in payload["permissions"]


# ============================================================================
# Session Lifecycle Tests
# ============================================================================

class TestSessionLifecycleWithAuth:
    """Tests for session lifecycle with authentication."""
    
    @pytest.fixture
    def setup_client(self, mock_orchestrator):
        """Set up test client with mocks."""
        from purple_team_gpt.backend.main import app
        from purple_team_gpt.backend import security
        security._rate_limiter = None
        
        # Patch the global orchestrator
        import purple_team_gpt.backend.main as main_module
        main_module.orchestrator = mock_orchestrator
        main_module.llm_engine = MagicMock()
        main_module.vector_store = MagicMock()
        main_module.feedback_store = MagicMock()
        
        # Also patch the routers module
        import purple_team_gpt.backend.routers.sessions as sessions_module
        sessions_module._orchestrator = mock_orchestrator
        
        yield TestClient(app), mock_orchestrator
    
    def test_create_session_authenticated(self, setup_client):
        """Test creating a session with authentication."""
        client, mock_orchestrator = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Create session
        response = client.post(
            "/api/v1/sessions/",
            json={"target": "192.168.1.1", "scope": "Test assessment"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["target"] == "192.168.1.1"
    
    def test_create_session_unauthenticated(self, setup_client):
        """Test that session creation requires authentication."""
        client, _ = setup_client
        
        # Try to create session without token
        response = client.post(
            "/api/v1/sessions/",
            json={"target": "192.168.1.1", "scope": "Test"}
        )
        
        assert response.status_code == 401
    
    def test_list_sessions_authenticated(self, setup_client):
        """Test listing sessions with authentication."""
        client, _ = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # List sessions
        response = client.get(
            "/api/v1/sessions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
    
    def test_get_session_authenticated(self, setup_client):
        """Test getting a specific session with authentication."""
        client, _ = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Get session
        response = client.get(
            "/api/v1/sessions/test-session-123",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    def test_start_session_authenticated(self, setup_client):
        """Test starting a session with authentication."""
        client, mock_orchestrator = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Start session
        response = client.post(
            "/api/v1/sessions/test-session-123/start",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
    
    def test_pause_session_authenticated(self, setup_client):
        """Test pausing a session with authentication."""
        client, _ = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Pause session
        response = client.post(
            "/api/v1/sessions/test-session-123/pause",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    def test_resume_session_authenticated(self, setup_client):
        """Test resuming a session with authentication."""
        client, _ = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Resume session
        response = client.post(
            "/api/v1/sessions/test-session-123/resume",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    def test_stop_session_authenticated(self, setup_client):
        """Test stopping a session with authentication."""
        client, _ = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Stop session
        response = client.post(
            "/api/v1/sessions/test-session-123/stop",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    def test_delete_session_authenticated(self, setup_client):
        """Test deleting a session with authentication."""
        client, _ = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Delete session
        response = client.delete(
            "/api/v1/sessions/test-session-123",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    def test_session_input_validation(self, setup_client):
        """Test that session input is validated."""
        client, _ = setup_client
        
        # Get token
        token_response = client.post("/auth/token")
        token = token_response.json()["access_token"]
        
        # Try to create session with malicious target
        response = client.post(
            "/api/v1/sessions/",
            json={"target": "target; rm -rf /", "scope": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should be rejected
        assert response.status_code == 400


# ============================================================================
# WebSocket Authentication Tests
# ============================================================================

class TestWebSocketAuthentication:
    """Tests for WebSocket authentication."""
    
    @pytest.fixture
    def setup_ws(self, mock_orchestrator):
        """Set up WebSocket test environment."""
        from purple_team_gpt.backend.main import app
        from purple_team_gpt.backend import security
        security._rate_limiter = None
        
        # Patch the global variables
        import purple_team_gpt.backend.main as main_module
        main_module.orchestrator = mock_orchestrator
        main_module.llm_engine = MagicMock()
        main_module.vector_store = MagicMock()
        main_module.feedback_store = MagicMock()
        
        # Also patch the websocket module
        import purple_team_gpt.backend.routers.websocket as ws_module
        ws_module._orchestrator = mock_orchestrator
        ws_module._vector_store = MagicMock()
        
        yield app
    
    def test_websocket_requires_token(self, setup_ws):
        """Test that WebSocket connection requires token."""
        client = TestClient(setup_ws)
        
        # Connect without token - should receive error message
        with client.websocket_connect("/ws/session/test-session-123") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "authentication" in data["message"].lower()
    
    def test_websocket_rejects_invalid_token(self, setup_ws):
        """Test that WebSocket rejects invalid tokens."""
        client = TestClient(setup_ws)
        
        # Connect with invalid token - should receive error message
        with client.websocket_connect("/ws/session/test-session-123?token=invalid") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "error"
    
    def test_websocket_accepts_valid_token(self, setup_ws):
        """Test that WebSocket accepts valid tokens."""
        from purple_team_gpt.backend.security import create_access_token
        
        client = TestClient(setup_ws)
        
        # Create valid token
        token = create_access_token({"sub": "test_user"})
        
        # Connect with valid token
        with client.websocket_connect(f"/ws/session/test-session-123?token={token}") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connected"
    
    def test_websocket_ping_pong(self, setup_ws):
        """Test WebSocket ping/pong functionality."""
        from purple_team_gpt.backend.security import create_access_token
        
        client = TestClient(setup_ws)
        token = create_access_token({"sub": "test_user"})
        
        with client.websocket_connect(f"/ws/session/test-session-123?token={token}") as websocket:
            # Receive initial connection messages (may be connected + session_state)
            # Just consume them
            for _ in range(3):
                msg = websocket.receive_json()
                if msg.get("type") == "session_state":
                    break
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Should receive pong
            response = websocket.receive_json()
            assert response["type"] == "pong"
    
    def test_websocket_handles_invalid_json(self, setup_ws):
        """Test that WebSocket handles invalid JSON gracefully."""
        from purple_team_gpt.backend.security import create_access_token
        
        client = TestClient(setup_ws)
        token = create_access_token({"sub": "test_user"})
        
        with client.websocket_connect(f"/ws/session/test-session-123?token={token}") as websocket:
            # Receive initial connection messages
            for _ in range(3):
                msg = websocket.receive_json()
                if msg.get("type") == "session_state":
                    break
            
            # Send invalid JSON
            websocket.send_text("not valid json")
            
            # Should receive error message
            response = websocket.receive_json()
            assert response["type"] == "error"
    
    def test_websocket_command_handling(self, setup_ws, mock_orchestrator):
        """Test WebSocket command handling."""
        from purple_team_gpt.backend.security import create_access_token
        
        client = TestClient(setup_ws)
        token = create_access_token({"sub": "test_user"})
        
        with client.websocket_connect(f"/ws/session/test-session-123?token={token}") as websocket:
            # Receive initial connection messages
            for _ in range(3):
                msg = websocket.receive_json()
                if msg.get("type") == "session_state":
                    break
            
            # Send pause command
            websocket.send_json({"type": "command", "command": "pause"})
            
            # Should receive command result
            response = websocket.receive_json()
            assert response["type"] == "command_result"
            assert response["command"] == "pause"


# ============================================================================
# End-to-End Flow Tests
# ============================================================================

class TestEndToEndFlow:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def full_setup(self, mock_orchestrator):
        """Full setup for end-to-end tests."""
        from purple_team_gpt.backend.main import app
        from purple_team_gpt.backend import security
        security._rate_limiter = None
        
        # Patch the global variables
        import purple_team_gpt.backend.main as main_module
        main_module.orchestrator = mock_orchestrator
        main_module.llm_engine = MagicMock()
        main_module.vector_store = MagicMock()
        main_module.feedback_store = MagicMock()
        
        # Also patch the routers
        import purple_team_gpt.backend.routers.sessions as sessions_module
        sessions_module._orchestrator = mock_orchestrator
        
        yield app, mock_orchestrator
    
    def test_full_session_lifecycle(self, full_setup):
        """Test complete session lifecycle from creation to deletion."""
        app, mock_orchestrator = full_setup
        client = TestClient(app)
        
        # 1. Get authentication token
        token_response = client.post("/auth/token")
        assert token_response.status_code == 200
        token = token_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Check health endpoint (unauthenticated)
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"
        
        # 3. Access root endpoint (rate limited but authenticated)
        root_response = client.get("/", headers=headers)
        assert root_response.status_code == 200
        
        # 4. Get status (requires auth)
        status_response = client.get("/status", headers=headers)
        assert status_response.status_code == 200
        
        # 5. Create a session
        create_response = client.post(
            "/api/v1/sessions/",
            json={"target": "192.168.1.1", "scope": "Full lifecycle test"},
            headers=headers
        )
        assert create_response.status_code == 201
        
        # 6. List sessions
        list_response = client.get("/api/v1/sessions/", headers=headers)
        assert list_response.status_code == 200
        
        # 7. Get specific session
        get_response = client.get("/api/v1/sessions/test-session-123", headers=headers)
        assert get_response.status_code == 200
        
        # 8. Start session
        start_response = client.post("/api/v1/sessions/test-session-123/start", headers=headers)
        assert start_response.status_code == 200
        
        # 9. Get session metrics
        metrics_response = client.get("/api/v1/sessions/test-session-123/metrics", headers=headers)
        assert metrics_response.status_code == 200
        
        # 10. Stop session
        stop_response = client.post("/api/v1/sessions/test-session-123/stop", headers=headers)
        assert stop_response.status_code == 200
        
        # 11. Delete session
        delete_response = client.delete("/api/v1/sessions/test-session-123", headers=headers)
        assert delete_response.status_code == 200
    
    def test_unauthorized_access_denied(self, full_setup):
        """Test that unauthorized access is properly denied."""
        app, _ = full_setup
        client = TestClient(app)
        
        protected_endpoints = [
            ("GET", "/status"),
            ("GET", "/api/v1/sessions/"),
            ("POST", "/api/v1/sessions/"),
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
            
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"


# ============================================================================
# Rate Limiting Integration Tests
# ============================================================================

class TestRateLimitingIntegration:
    """Integration tests for rate limiting."""
    
    def test_rate_limiting_enforced(self):
        """Test that rate limiting is actually enforced."""
        # Set strict rate limits
        os.environ["APP_RATE_LIMIT_REQUESTS"] = "5"
        os.environ["APP_RATE_LIMIT_WINDOW_SECONDS"] = "10"
        
        # Clear any cached settings
        from purple_team_gpt.config import get_settings
        get_settings.cache_clear()
        
        from purple_team_gpt.backend.main import app
        from purple_team_gpt.backend import security
        security._rate_limiter = None
        
        client = TestClient(app)
        
        # Make many requests quickly
        responses = []
        for i in range(15):
            response = client.get("/")
            responses.append(response.status_code)
        
        # Some requests should be rate limited (429)
        assert 429 in responses, f"Rate limiting should kick in. Got statuses: {set(responses)}"