"""Tests for Token Budget Management."""

import pytest
from purple_team_gpt.core.llm.budget import TokenBudget


class TestTokenBudgetInitialization:
    """Tests for TokenBudget initialization."""

    def test_init_with_openai_gpt4o(self):
        """Test initialization with OpenAI GPT-4o model."""
        budget = TokenBudget(provider="openai", model="gpt-4o")
        assert budget.provider == "openai"
        assert budget.model == "gpt-4o"
        assert budget.max_context_tokens == 128000

    def test_init_with_anthropic_claude(self):
        """Test initialization with Anthropic Claude model."""
        budget = TokenBudget(provider="anthropic", model="claude-sonnet-4-20250514")
        assert budget.provider == "anthropic"
        assert budget.model == "claude-sonnet-4-20250514"
        assert budget.max_context_tokens == 200000

    def test_init_with_gemini(self):
        """Test initialization with Gemini model."""
        budget = TokenBudget(provider="gemini", model="gemini-2.0-flash")
        assert budget.provider == "gemini"
        assert budget.model == "gemini-2.0-flash"
        assert budget.max_context_tokens == 1000000

    def test_init_with_unknown_model(self):
        """Test initialization with unknown model defaults to 4096."""
        budget = TokenBudget(provider="unknown", model="unknown-model")
        assert budget.max_context_tokens == 4096

    def test_init_with_custom_reserved_tokens(self):
        """Test initialization with custom reserved tokens."""
        budget = TokenBudget(provider="openai", model="gpt-4o", reserved_for_response=8192)
        assert budget.reserved_for_response == 8192
        assert budget.available_for_input == 128000 - 8192


class TestTokenCounting:
    """Tests for token counting functionality."""

    def test_count_tokens_estimation(self):
        """Test token count estimation (~4 chars per token)."""
        budget = TokenBudget(provider="openai", model="gpt-4o")

        # Simple message
        messages = [{"role": "user", "content": "Hello world"}]
        token_count = budget.count_tokens(messages)

        # "user" (4 chars) + "Hello world" (11 chars) + 4 overhead = 19 chars
        # 19 / 4 ≈ 4 tokens
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_count_tokens_multiple_messages(self):
        """Test token counting with multiple messages."""
        budget = TokenBudget(provider="openai", model="gpt-4o")

        messages = [
            {"role": "system", "content": "You are a security expert."},
            {"role": "user", "content": "What is nmap?"},
            {"role": "assistant", "content": "Nmap is a network scanning tool."},
        ]
        token_count = budget.count_tokens(messages)

        # Should count all messages
        assert token_count > 0

    def test_count_tokens_empty_messages(self):
        """Test token counting with empty messages list."""
        budget = TokenBudget(provider="openai", model="gpt-4o")

        messages = []
        token_count = budget.count_tokens(messages)

        assert token_count == 0


class TestBudgetChecking:
    """Tests for budget checking functionality."""

    def test_check_budget_within_limits(self):
        """Test budget check when messages fit within limits."""
        budget = TokenBudget(provider="openai", model="gpt-4o", reserved_for_response=4096)

        # Small message that should fit
        messages = [{"role": "user", "content": "Hello"}]

        assert budget.check_budget(messages) is True

    def test_check_budget_exceeds_limits(self):
        """Test budget check when messages exceed limits."""
        # Use small limit to force overflow
        budget = TokenBudget(provider="unknown", model="unknown", reserved_for_response=100)

        # Create large message that will exceed the small limit
        # Unknown model defaults to 4096 tokens, reserved is 100, so available is 3996
        # We need more than 3996 tokens (more than ~16000 chars)
        large_content = "x" * 20000
        messages = [{"role": "user", "content": large_content}]

        assert budget.check_budget(messages) is False

    def test_check_budget_exact_fit(self):
        """Test budget check when messages exactly fit."""
        budget = TokenBudget(provider="openai", model="gpt-4o", reserved_for_response=4096)

        # Small message
        messages = [{"role": "user", "content": "Test"}]

        # Should fit
        assert budget.check_budget(messages) is True


class TestMessageTruncation:
    """Tests for message truncation functionality."""

    def test_truncate_messages_no_truncation_needed(self):
        """Test truncation when messages already fit budget."""
        budget = TokenBudget(provider="openai", model="gpt-4o", reserved_for_response=4096)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]

        result = budget.truncate_messages(messages)

        # Should return same messages since they fit
        assert len(result) == 2
        assert result == messages

    def test_truncate_messages_preserves_system(self):
        """Test truncation preserves system prompt."""
        # Use small limit to force truncation
        budget = TokenBudget(provider="unknown", model="unknown", reserved_for_response=4000)

        system_msg = {"role": "system", "content": "You are a security expert."}
        user_msg = {"role": "user", "content": "Hello"}

        messages = [system_msg, user_msg]
        result = budget.truncate_messages(messages, preserve_system=True)

        # System message should be preserved
        assert system_msg in result
        assert result[0] == system_msg

    def test_truncate_messages_removes_oldest_user_messages(self):
        """Test truncation removes oldest user messages first."""
        # Use very small limit to force truncation
        # Unknown model defaults to 4096 tokens
        # With reserved=4075, available = 21 tokens (~84 chars)
        budget = TokenBudget(provider="unknown", model="unknown", reserved_for_response=4075)

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "First message - this should be removed"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Second message"},
        ]

        result = budget.truncate_messages(messages, preserve_system=True)

        # System should be preserved
        assert any(msg.get("role") == "system" for msg in result)

        # Result should be shorter than original
        assert len(result) < len(messages)

    def test_truncate_messages_without_preserve_system(self):
        """Test truncation without preserving system prompt."""
        budget = TokenBudget(provider="unknown", model="unknown", reserved_for_response=200)

        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"},
        ]

        result = budget.truncate_messages(messages, preserve_system=False)

        # When preserve_system=False, all messages can be truncated
        # The most recent messages should be kept
        assert len(result) <= len(messages)


class TestProviderLimits:
    """Tests for provider-specific context limits."""

    def test_openai_limits(self):
        """Test OpenAI model limits."""
        gpt4o = TokenBudget(provider="openai", model="gpt-4o")
        gpt4o_mini = TokenBudget(provider="openai", model="gpt-4o-mini")
        gpt4_turbo = TokenBudget(provider="openai", model="gpt-4-turbo")

        assert gpt4o.max_context_tokens == 128000
        assert gpt4o_mini.max_context_tokens == 128000
        assert gpt4_turbo.max_context_tokens == 128000

    def test_anthropic_limits(self):
        """Test Anthropic model limits."""
        claude_sonnet = TokenBudget(provider="anthropic", model="claude-sonnet-4-20250514")
        claude_haiku = TokenBudget(provider="anthropic", model="claude-3-5-haiku-20241022")

        assert claude_sonnet.max_context_tokens == 200000
        assert claude_haiku.max_context_tokens == 200000

    def test_gemini_limits(self):
        """Test Gemini model limits."""
        gemini_flash = TokenBudget(provider="gemini", model="gemini-2.0-flash")
        gemini_pro = TokenBudget(provider="gemini", model="gemini-1.5-pro")

        assert gemini_flash.max_context_tokens == 1000000
        assert gemini_pro.max_context_tokens == 2000000

    def test_groq_limits(self):
        """Test Groq model limits."""
        llama = TokenBudget(provider="groq", model="llama-3.3-70b-versatile")

        assert llama.max_context_tokens == 128000

    def test_ollama_limits(self):
        """Test Ollama model limits."""
        llama = TokenBudget(provider="ollama", model="llama3.2")

        assert llama.max_context_tokens == 128000


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_messages_list(self):
        """Test with empty messages list."""
        budget = TokenBudget(provider="openai", model="gpt-4o")

        assert budget.check_budget([]) is True
        assert budget.truncate_messages([]) == []

    def test_only_system_message(self):
        """Test with only system message."""
        budget = TokenBudget(provider="openai", model="gpt-4o")

        messages = [{"role": "system", "content": "System prompt"}]

        assert budget.check_budget(messages) is True
        result = budget.truncate_messages(messages)
        assert len(result) == 1

    def test_message_with_missing_content(self):
        """Test message with missing content field."""
        budget = TokenBudget(provider="openai", model="gpt-4o")

        messages = [{"role": "user"}]

        # Should handle missing content gracefully
        token_count = budget.count_tokens(messages)
        assert isinstance(token_count, int)

    def test_case_insensitive_provider(self):
        """Test that provider name is case insensitive."""
        budget1 = TokenBudget(provider="OpenAI", model="gpt-4o")
        budget2 = TokenBudget(provider="OPENAI", model="gpt-4o")

        assert budget1.max_context_tokens == 128000
        assert budget2.max_context_tokens == 128000
