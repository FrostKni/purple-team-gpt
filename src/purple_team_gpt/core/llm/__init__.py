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
    create_engine,
)

__all__ = [
    "Conversation",
    "LLMEngine",
    "Message",
    "Provider",
    "ProviderConfig",
    "create_engine",
]