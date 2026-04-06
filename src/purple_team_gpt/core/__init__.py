"""Core functionality for Purple Team GPT.

This module provides the core components:
- Orchestrator: Coordinates Red and Blue agents
- LLM Engine: Multi-provider LLM integration
- Vector Store: RAG capabilities

Usage:
    from purple_team_gpt.core import PurpleOrchestrator, create_orchestrator
    from purple_team_gpt.core.llm import create_engine
    from purple_team_gpt.core.rag import create_vector_store
    
    engine = create_engine()
    vector_store = create_vector_store()
    orchestrator = create_orchestrator(engine, vector_store)
"""

# Lazy imports to avoid circular dependency with agents module
def __getattr__(name: str):
    if name in ("PurpleOrchestrator", "Session", "SessionStatus", "AgentEvent", "create_orchestrator"):
        from purple_team_gpt.core.orchestrator import (
            AgentEvent,
            PurpleOrchestrator,
            Session,
            SessionStatus,
            create_orchestrator,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Orchestrator
    "PurpleOrchestrator",
    "Session",
    "SessionStatus",
    "AgentEvent",
    "create_orchestrator",
]