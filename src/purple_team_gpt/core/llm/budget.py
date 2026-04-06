"""Token budget management for LLM context windows."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TokenBudget:
    """Prevent context window overflow and manage token costs."""

    PROVIDER_LIMITS: Dict[str, Dict[str, int]] = {
        "openai": {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4-turbo": 128000,
        },
        "anthropic": {
            "claude-sonnet-4-20250514": 200000,
            "claude-3-5-haiku-20241022": 200000,
        },
        "gemini": {
            "gemini-2.0-flash": 1000000,
            "gemini-1.5-pro": 2000000,
        },
        "groq": {
            "llama-3.3-70b-versatile": 128000,
        },
        "ollama": {
            "llama3.2": 128000,
        },
    }

    def __init__(self, provider: str, model: str, reserved_for_response: int = 4096):
        """Initialize token budget for a specific provider and model.

        Args:
            provider: LLM provider name (e.g., "openai", "anthropic")
            model: Model name (e.g., "gpt-4o", "claude-sonnet-4-20250514")
            reserved_for_response: Tokens reserved for the response (default: 4096)
        """
        self.provider = provider.lower()
        self.model = model
        self.max_context_tokens = self._get_default_limit()
        self.reserved_for_response = reserved_for_response
        self.available_for_input = self.max_context_tokens - reserved_for_response

    def _get_default_limit(self) -> int:
        """Get default context limit for the provider/model combination.

        Returns:
            Maximum context tokens for the model, or 4096 if unknown.
        """
        provider_limits = self.PROVIDER_LIMITS.get(self.provider, {})
        return provider_limits.get(self.model, 4096)

    def count_tokens(self, messages: List[Dict]) -> int:
        """Estimate token count (~4 chars per token).

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.

        Returns:
            Estimated token count.
        """
        total_chars = 0
        for msg in messages:
            total_chars += len(msg.get("role", ""))
            total_chars += len(msg.get("content", ""))
            total_chars += 4  # overhead
        return total_chars // 4

    def check_budget(self, messages: List[Dict]) -> bool:
        """Check if messages fit within budget.

        Args:
            messages: List of message dictionaries.

        Returns:
            True if messages fit within budget, False otherwise.
        """
        return self.count_tokens(messages) <= self.available_for_input

    def truncate_messages(self, messages: List[Dict], preserve_system: bool = True) -> List[Dict]:
        """Truncate messages to fit budget, preserving system prompt.

        Args:
            messages: List of message dictionaries to truncate.
            preserve_system: Whether to preserve system messages (default: True).

        Returns:
            Truncated list of messages that fits within budget.
        """
        if self.check_budget(messages):
            return messages

        # Separate system messages if preserving
        system_msgs = [m for m in messages if m.get("role") == "system"] if preserve_system else []
        other_msgs = (
            [m for m in messages if m.get("role") != "system"]
            if preserve_system
            else messages.copy()
        )

        # Calculate available tokens after system messages
        system_tokens = self.count_tokens(system_msgs)
        available = self.available_for_input - system_tokens

        # Build result from the most recent messages (reverse order)
        result = []
        for msg in reversed(other_msgs):
            msg_tokens = self.count_tokens([msg])
            if self.count_tokens(result) + msg_tokens <= available:
                result.insert(0, msg)
            else:
                break

        return system_msgs + result
