"""Tests for the Agent Memory system."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from purple_team_gpt.agents.memory import AgentLearning, AgentMemory


class TestAgentLearning:
    """Tests for the AgentLearning dataclass."""

    def test_learning_creation(self):
        """Test creating a learning."""
        learning = AgentLearning(
            pattern="SQL injection found",
            context="Testing web application",
            success=True,
        )
        assert learning.pattern == "SQL injection found"
        assert learning.context == "Testing web application"
        assert learning.success is True
        assert learning.tool_used is None
        assert learning.outcome is None

    def test_learning_with_all_fields(self):
        """Test creating a learning with all fields."""
        learning = AgentLearning(
            pattern="XSS vulnerability",
            context="Input field testing",
            success=True,
            tool_used="burpsuite",
            outcome="Reflected XSS detected",
        )
        assert learning.pattern == "XSS vulnerability"
        assert learning.tool_used == "burpsuite"
        assert learning.outcome == "Reflected XSS detected"

    def test_learning_to_dict(self):
        """Test converting learning to dictionary."""
        learning = AgentLearning(
            pattern="Open port 22",
            context="Network scan",
            success=True,
            tool_used="nmap",
            outcome="SSH exposed",
        )

        result = learning.to_dict()

        assert result["pattern"] == "Open port 22"
        assert result["context"] == "Network scan"
        assert result["success"] is True
        assert result["tool_used"] == "nmap"
        assert result["outcome"] == "SSH exposed"
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)


class TestAgentMemory:
    """Tests for the AgentMemory class."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        store = MagicMock()
        store.add = AsyncMock(return_value=["doc-id-1"])
        store.query = AsyncMock(
            return_value={
                "ids": ["doc-id-1"],
                "documents": ["Pattern: SQL injection\nContext: Testing\nSuccess: True"],
                "metadatas": [
                    {
                        "agent_id": "agent-1",
                        "pattern": "SQL injection",
                        "success": True,
                        "tool": "sqlmap",
                        "outcome": "Data extracted",
                    }
                ],
                "distances": [0.1],
            }
        )
        return store

    def test_initialization(self, mock_vector_store):
        """Test agent memory initialization."""
        memory = AgentMemory(
            agent_id="test-agent",
            vector_store=mock_vector_store,
        )

        assert memory.agent_id == "test-agent"
        assert memory.vector_store == mock_vector_store
        assert memory.collection_name == "agent_memory"
        assert memory._sessions == {}

    def test_initialization_custom_collection(self, mock_vector_store):
        """Test agent memory with custom collection name."""
        memory = AgentMemory(
            agent_id="test-agent",
            vector_store=mock_vector_store,
            collection_name="custom_memory",
        )

        assert memory.collection_name == "custom_memory"

    @pytest.mark.asyncio
    async def test_save_session(self, mock_vector_store):
        """Test saving session state."""
        memory = AgentMemory(
            agent_id="test-agent",
            vector_store=mock_vector_store,
        )

        state = {
            "target": "192.168.1.1",
            "steps": 10,
            "findings": 3,
        }

        await memory.save_session("session-123", state)

        assert "session-123" in memory._sessions
        saved = memory._sessions["session-123"]
        assert saved["target"] == "192.168.1.1"
        assert saved["steps"] == 10
        assert saved["findings"] == 3
        assert saved["agent_id"] == "test-agent"
        assert "saved_at" in saved

    @pytest.mark.asyncio
    async def test_load_session(self, mock_vector_store):
        """Test loading session state."""
        memory = AgentMemory(
            agent_id="test-agent",
            vector_store=mock_vector_store,
        )

        # Save a session first
        state = {"target": "example.com", "completed": True}
        await memory.save_session("session-456", state)

        # Load it back
        loaded = await memory.load_session("session-456")

        assert loaded is not None
        assert loaded["target"] == "example.com"
        assert loaded["completed"] is True

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, mock_vector_store):
        """Test loading a session that doesn't exist."""
        memory = AgentMemory(
            agent_id="test-agent",
            vector_store=mock_vector_store,
        )

        result = await memory.load_session("nonexistent-session")

        assert result is None

    @pytest.mark.asyncio
    async def test_save_learning(self, mock_vector_store):
        """Test saving a learning to vector store."""
        memory = AgentMemory(
            agent_id="agent-1",
            vector_store=mock_vector_store,
        )

        learning = AgentLearning(
            pattern="SQL injection",
            context="Web application testing on login form",
            success=True,
            tool_used="sqlmap",
            outcome="Extracted user credentials",
        )

        await memory.save_learning(learning)

        # Verify vector store was called correctly
        mock_vector_store.add.assert_called_once()
        call_args = mock_vector_store.add.call_args

        assert call_args.kwargs["collection_name"] == "agent_memory"
        assert len(call_args.kwargs["documents"]) == 1
        assert "SQL injection" in call_args.kwargs["documents"][0]

        # Check metadata
        metadata = call_args.kwargs["metadatas"][0]
        assert metadata["agent_id"] == "agent-1"
        assert metadata["pattern"] == "SQL injection"
        assert metadata["success"] is True
        assert metadata["tool"] == "sqlmap"

    @pytest.mark.asyncio
    async def test_get_relevant_learnings(self, mock_vector_store):
        """Test retrieving relevant learnings."""
        memory = AgentMemory(
            agent_id="agent-1",
            vector_store=mock_vector_store,
        )

        learnings = await memory.get_relevant_learnings(
            context="Testing login form for SQL injection",
            n_results=5,
        )

        assert len(learnings) == 1
        learning = learnings[0]
        assert learning.pattern == "SQL injection"
        assert learning.success is True
        assert learning.tool_used == "sqlmap"

        # Verify query was called correctly
        mock_vector_store.query.assert_called_once()
        call_args = mock_vector_store.query.call_args
        assert call_args.kwargs["collection_name"] == "agent_memory"
        assert call_args.kwargs["n_results"] == 5
        assert call_args.kwargs["where"]["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_get_relevant_learnings_empty_results(self, mock_vector_store):
        """Test retrieving learnings when none exist."""
        mock_vector_store.query = AsyncMock(
            return_value={
                "ids": [],
                "documents": [],
                "metadatas": [],
                "distances": [],
            }
        )

        memory = AgentMemory(
            agent_id="agent-2",
            vector_store=mock_vector_store,
        )

        learnings = await memory.get_relevant_learnings(
            context="New context",
            n_results=5,
        )

        assert learnings == []

    @pytest.mark.asyncio
    async def test_get_relevant_learnings_error_handling(self, mock_vector_store):
        """Test that errors during retrieval are handled gracefully."""
        mock_vector_store.query = AsyncMock(side_effect=Exception("Connection error"))

        memory = AgentMemory(
            agent_id="agent-3",
            vector_store=mock_vector_store,
        )

        # Should not raise, should return empty list
        learnings = await memory.get_relevant_learnings(
            context="Any context",
            n_results=5,
        )

        assert learnings == []

    @pytest.mark.asyncio
    async def test_save_multiple_sessions(self, mock_vector_store):
        """Test saving multiple sessions."""
        memory = AgentMemory(
            agent_id="test-agent",
            vector_store=mock_vector_store,
        )

        await memory.save_session("session-1", {"target": "host1"})
        await memory.save_session("session-2", {"target": "host2"})
        await memory.save_session("session-3", {"target": "host3"})

        assert len(memory._sessions) == 3

        # Verify each can be loaded
        assert (await memory.load_session("session-1"))["target"] == "host1"
        assert (await memory.load_session("session-2"))["target"] == "host2"
        assert (await memory.load_session("session-3"))["target"] == "host3"

    @pytest.mark.asyncio
    async def test_save_learning_without_optional_fields(self, mock_vector_store):
        """Test saving a learning without optional fields."""
        memory = AgentMemory(
            agent_id="agent-1",
            vector_store=mock_vector_store,
        )

        learning = AgentLearning(
            pattern="Open port 80",
            context="Network scan",
            success=False,
        )

        await memory.save_learning(learning)

        # Verify it was saved
        mock_vector_store.add.assert_called_once()
        metadata = mock_vector_store.add.call_args.kwargs["metadatas"][0]
        assert metadata["tool"] == ""  # Should be empty string, not None
        assert metadata["outcome"] == ""
