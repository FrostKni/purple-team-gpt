"""Pytest fixtures for Purple Team GPT tests."""

import asyncio
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# ============================================================================
# Settings Fixtures (no imports needed)
# ============================================================================

@pytest.fixture
def llm_settings():
    """Create mock LLM settings."""
    # Use MagicMock to avoid circular imports
    settings = MagicMock()
    settings.openai_api_key = "test-openai-key"
    settings.anthropic_api_key = "test-anthropic-key"
    settings.groq_api_key = "test-groq-key"
    settings.deepseek_api_key = "test-deepseek-key"
    settings.mistral_api_key = None  # New field
    settings.ollama_base_url = "http://localhost:11434"
    settings.default_provider = "openai"
    settings.default_model = "gpt-4o"
    settings.temperature = 0.7
    settings.max_tokens = 4096
    settings.enable_failover = True  # New field
    settings.openai_compatible_api_key = None  # New field
    settings.openai_compatible_base_url = None  # New field
    settings.openai_compatible_model = "local-model"  # New field
    return settings


@pytest.fixture
def chroma_settings():
    """Create mock ChromaDB settings."""
    settings = MagicMock()
    settings.host = "localhost"
    settings.port = 8001
    settings.persist_dir = "./test_data/chromadb"
    return settings


@pytest.fixture
def settings(llm_settings, chroma_settings):
    """Create mock settings."""
    settings = MagicMock()
    settings.llm = llm_settings
    settings.chroma = chroma_settings
    settings.openai_compatible_endpoints = []  # New field
    return settings


# ============================================================================
# LLM Engine Fixtures
# ============================================================================

@pytest.fixture
def mock_litellm_response():
    """Create a mock LiteLLM response."""
    mock_choice = MagicMock()
    mock_choice.message.content = "This is a test response from the LLM."
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.fixture
def mock_acompletion(mock_litellm_response):
    """Mock the litellm acompletion function."""
    async def mock_completion(*args, **kwargs):
        if kwargs.get("stream"):
            # Return async generator for streaming
            async def stream_gen():
                for chunk in ["Test ", "streaming ", "response"]:
                    mock_delta = MagicMock()
                    mock_delta.content = chunk
                    mock_choice = MagicMock()
                    mock_choice.delta = mock_delta
                    mock_chunk = MagicMock()
                    mock_chunk.choices = [mock_choice]
                    yield mock_chunk
            return stream_gen()
        return mock_litellm_response
    
    return AsyncMock(side_effect=mock_completion)


@pytest.fixture
def llm_engine(llm_settings, mock_acompletion):
    """Create an LLM engine with mocked LiteLLM."""
    with patch("purple_team_gpt.core.llm.engine.acompletion", mock_acompletion):
        from purple_team_gpt.core.llm.engine import LLMEngine
        yield LLMEngine(llm_settings)


@pytest.fixture
def mock_event_callback():
    """Create a mock event callback for orchestrator tests."""
    return MagicMock()


# ============================================================================
# Vector Store Fixtures
# ============================================================================

@pytest.fixture
def mock_chroma_client():
    """Create a mock ChromaDB client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_collection():
    """Create a mock ChromaDB collection."""
    collection = MagicMock()
    collection.count.return_value = 10
    collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }
    return collection


@pytest.fixture
def mock_chroma_collection(mock_collection):
    """Alias for mock_collection for backward compatibility with tests."""
    return mock_collection


@pytest.fixture
def mock_embedding_engine():
    """Create a mock embedding engine."""
    engine = MagicMock()
    engine.embed = AsyncMock(return_value=[[0.1] * 384])  # Mock embedding
    engine.dimension = 384
    return engine


@pytest.fixture
def vector_store(chroma_settings, mock_embedding_engine, mock_chroma_client, mock_collection):
    """Create a vector store with mocked ChromaDB."""
    with patch("purple_team_gpt.core.rag.vector_store.chromadb.HttpClient", return_value=mock_chroma_client), \
         patch("purple_team_gpt.core.rag.vector_store.chromadb.PersistentClient", return_value=mock_chroma_client):
        # Return the same mock collection for any collection name
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        mock_chroma_client.get_collection.return_value = mock_collection
        from purple_team_gpt.core.rag.vector_store import VectorStore
        store = VectorStore(chroma_settings, mock_embedding_engine)
        store._client = mock_chroma_client
        yield store


# ============================================================================
# Agent Fixtures
# ============================================================================

@pytest.fixture
def sample_finding():
    """Create a sample finding."""
    from dataclasses import dataclass
    from datetime import datetime
    
    @dataclass
    class Finding:
        title: str
        severity: str
        description: str
        evidence: str = ""
        recommendation: str = ""
        tool: str = ""
        timestamp: datetime = None
    
    return Finding(
        title="Test Finding",
        severity="High",
        description="Test description",
        evidence="Test evidence",
        recommendation="Test recommendation",
        tool="test_tool",
    )


@pytest.fixture
def mock_finding_callback():
    """Create a mock finding callback."""
    return MagicMock()


@pytest.fixture
def mock_step_callback():
    """Create a mock step callback."""
    return MagicMock()


@pytest.fixture
def mock_output_callback():
    """Create a mock output callback."""
    return MagicMock()


@pytest.fixture
def red_agent(llm_engine, vector_store, mock_finding_callback, mock_step_callback, mock_output_callback):
    """Create a Red Agent for testing."""
    from purple_team_gpt.agents.red_agent import RedAgent
    return RedAgent(
        llm_engine,
        vector_store,
        on_finding=mock_finding_callback,
        on_step=mock_step_callback,
        on_output=mock_output_callback,
    )


@pytest.fixture
def blue_agent(llm_engine, vector_store):
    """Create a Blue Agent for testing."""
    from purple_team_gpt.agents.blue_agent import BlueAgent
    return BlueAgent(llm_engine, vector_store)


# ============================================================================
# Orchestrator Fixtures
# ============================================================================

@pytest.fixture
def orchestrator(llm_engine, vector_store):
    """Create a Purple Orchestrator for testing."""
    from purple_team_gpt.core.orchestrator import PurpleOrchestrator
    return PurpleOrchestrator(llm_engine, vector_store)


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_log_data():
    """Sample log data for testing."""
    return """
    Mar 10 10:00:00 server sshd[1234]: Failed password for root from 192.168.1.100 port 22
    Mar 10 10:01:00 server sshd[1235]: Accepted password for user from 192.168.1.50 port 22
    Mar 10 10:02:00 server kernel: [UFW BLOCK] IN=eth0 SRC=10.0.0.1 DST=192.168.1.1
    """


@pytest.fixture
def sample_attack_patterns():
    """Sample attack patterns for RAG."""
    return [
        "SQL injection detected in login form using UNION SELECT",
        "XSS attack found in search parameter with script injection",
        "Directory traversal attempt in file download endpoint",
    ]


@pytest.fixture
def sample_defense_patterns():
    """Sample defense patterns for RAG."""
    return [
        "Blocked SQL injection by sanitizing input parameters",
        "Implemented CSP headers to prevent XSS attacks",
        "Restricted file access to prevent directory traversal",
    ]