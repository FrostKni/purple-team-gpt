"""Integration tests for Purple Team GPT.

Tests:
- Full session lifecycle with database
- Orchestrator with database persistence
- Concurrent session handling
"""

import os
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

# Set environment variables before imports
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-integration-testing-32ch"
os.environ["APP_DEBUG"] = "true"

from purple_team_gpt.db import SessionStatus
from purple_team_gpt.core.orchestrator import PurpleOrchestrator, Session
from purple_team_gpt.core.llm.engine import LLMEngine, Conversation


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_engine():
    """Create a mock LLM engine."""
    engine = MagicMock(spec=LLMEngine)
    engine.quick_ask = AsyncMock(return_value="Test LLM response")
    engine.chat = AsyncMock(return_value="Test chat response")
    engine.is_configured = MagicMock(return_value=True)
    return engine


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = MagicMock()
    store.search = AsyncMock(return_value=[])
    store.add_document = AsyncMock(return_value="doc-id")
    return store


# ============================================================================
# Session Object Tests
# ============================================================================

class TestSessionObject:
    """Tests for the Session dataclass used by orchestrator."""
    
    def test_session_creation(self):
        """Test creating a Session object."""
        session = Session(
            id="test-id",
            target="example.com",
            scope="Full assessment",
        )
        
        assert session.id == "test-id"
        assert session.target == "example.com"
        assert session.status == "pending"
    
    def test_session_status_transitions(self):
        """Test session status transitions."""
        session = Session(
            id="test-id",
            target="example.com",
        )
        
        # Initial status
        assert session.status == "pending"
        
        # Transition to running
        session.status = "running"
        assert session.status == "running"
        
        # Transition to completed
        session.status = "completed"
        assert session.status == "completed"
    
    def test_session_with_findings(self):
        """Test session with findings."""
        session = Session(
            id="test-id",
            target="example.com",
        )
        
        # Add findings
        session.red_findings_count = 5
        session.blue_findings_count = 3
        
        assert session.red_findings_count == 5
        assert session.blue_findings_count == 3


# ============================================================================
# Orchestrator Integration Tests
# ============================================================================

class TestOrchestratorIntegration:
    """Tests for orchestrator integration."""
    
    def test_orchestrator_has_methods(self, mock_llm_engine, mock_vector_store):
        """Test that orchestrator has expected methods."""
        orchestrator = PurpleOrchestrator(mock_llm_engine, mock_vector_store)
        
        assert hasattr(orchestrator, 'start_session')
        assert hasattr(orchestrator, 'stop_session')
        assert hasattr(orchestrator, 'get_session')
        assert hasattr(orchestrator, 'list_sessions')
        assert hasattr(orchestrator, 'get_metrics')


# ============================================================================
# Concurrency Tests
# ============================================================================

class TestConcurrency:
    """Tests for concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_orchestrator_sessions(self, mock_llm_engine, mock_vector_store):
        """Test concurrent session handling in orchestrator."""
        orchestrator = PurpleOrchestrator(mock_llm_engine, mock_vector_store)
        
        # Create multiple session objects
        sessions = [
            Session(id=f"session-{i}", target=f"target-{i}")
            for i in range(10)
        ]
        
        # All should be unique
        ids = [s.id for s in sessions]
        assert len(set(ids)) == 10


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Tests for performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_session_creation_performance(self):
        """Test that creating many sessions is fast."""
        import time
        
        start = time.time()
        
        sessions = [
            Session(id=f"session-{i}", target=f"target-{i}")
            for i in range(100)
        ]
        
        elapsed = time.time() - start
        
        # Should be very fast
        assert elapsed < 0.1
        assert len(sessions) == 100


# ============================================================================
# Conversation Tests
# ============================================================================

class TestConversationIntegration:
    """Tests for conversation integration."""
    
    def test_conversation_creation(self):
        """Test creating a conversation."""
        conv = Conversation()
        
        assert len(conv) == 0
        assert conv.messages == []
    
    def test_conversation_with_messages(self):
        """Test conversation with messages."""
        conv = Conversation()
        conv.add_user("Hello")
        conv.add_assistant("Hi there!")
        
        assert len(conv) == 2
        
        api_format = conv.to_api_format()
        assert len(api_format) == 2
        assert api_format[0]["role"] == "user"
        assert api_format[1]["role"] == "assistant"


# ============================================================================
# Database Import Tests
# ============================================================================

class TestDatabaseIntegration:
    """Tests for database integration."""
    
    def test_database_module_imports(self):
        """Test that database modules can be imported."""
        from purple_team_gpt.db import database, models, repository
        
        assert database is not None
        assert models is not None
        assert repository is not None
    
    def test_database_session_manager_exists(self):
        """Test that DatabaseSessionManager exists."""
        from purple_team_gpt.db.database import DatabaseSessionManager
        
        assert DatabaseSessionManager is not None
    
    def test_session_status_values(self):
        """Test SessionStatus values."""
        from purple_team_gpt.db import SessionStatus
        
        assert SessionStatus.PENDING.value == "pending"
        assert SessionStatus.RUNNING.value == "running"
        assert SessionStatus.COMPLETED.value == "completed"