"""RAG pipeline and vector storage for Purple Team GPT.

This module provides:
- EmbeddingEngine: Generate embeddings using sentence-transformers (local) or OpenAI
- VectorStore: ChromaDB-based vector store for RAG operations

Collections:
- attack_patterns: Red team attack techniques and patterns
- defense_patterns: Blue team defense strategies and patterns
- feedback_store: Feedback from operations for adaptive learning
- session_logs: Logs from security testing sessions

Usage:
    from purple_team_gpt.core.rag import EmbeddingEngine, VectorStore
    from purple_team_gpt.config import get_settings
    
    # Create embedding engine
    engine = EmbeddingEngine(provider="local")  # or "openai"
    
    # Create vector store
    settings = get_settings()
    store = VectorStore(settings.chroma, engine)
    
    # Add documents
    await store.add("attack_patterns", ["SQL injection pattern..."])
    
    # Query for context
    context = await store.get_context("web application attacks")
"""

from purple_team_gpt.core.rag.embeddings import (
    EmbeddingEngine,
    EmbeddingProvider,
    create_embedding_engine,
)
from purple_team_gpt.core.rag.vector_store import (
    CollectionName,
    VectorStore,
    create_vector_store,
)

__all__ = [
    # Embeddings
    "EmbeddingEngine",
    "EmbeddingProvider",
    "create_embedding_engine",
    # Vector Store
    "VectorStore",
    "CollectionName",
    "create_vector_store",
]