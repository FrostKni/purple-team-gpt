"""
LLM Engine for Purple Team GPT.

Multi-provider LLM support with LiteLLM for:
- OpenAI
- Anthropic
- Groq
- Ollama
- DeepSeek
- Mistral
- Any OpenAI-compatible API (OpenRouter, LocalAI, vLLM, LMStudio, etc.)
"""

from purple_team_gpt.core.llm.engine import (
    Conversation,
    LLMEngine,
    Message,
    Provider,
    ProviderConfig,
)

__all__ = [
    "Conversation",
    "LLMEngine",
    "Message",
    "Provider",
    "ProviderConfig",
]


def create_engine(settings=None, openai_compatible_endpoints=None):
    """Create an LLM engine with optional settings.
    
    Args:
        settings: LLMSettings instance (optional, will use defaults if not provided)
        openai_compatible_endpoints: List of OpenAICompatibleEndpoint (optional)
    
    Returns:
        LLMEngine instance
    """
    if settings is None:
        from purple_team_gpt.config import get_settings
        settings = get_settings().llm
    return LLMEngine(settings, openai_compatible_endpoints)