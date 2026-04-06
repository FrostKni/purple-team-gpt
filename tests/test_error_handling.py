"""Additional unit tests for error handling, edge cases, and retry logic.

Tests:
- Error handling paths
- Edge cases in security validation
- Retry logic in LLM engine
- Boundary conditions
"""

import os
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

# Set environment variables before imports
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-unit-testing-32-char!"
os.environ["APP_DEBUG"] = "true"

from purple_team_gpt.core.llm.engine import (
    LLMEngine,
    Conversation,
    Message,
    Provider,
    is_transient_error,
    with_retry,
    TRANSIENT_ERROR_PATTERNS,
)
from purple_team_gpt.config import (
    LLMSettings,
    validate_url_for_ssrf,
)


# ============================================================================
# Transient Error Detection Tests
# ============================================================================

class TestTransientErrorDetection:
    """Tests for transient error detection."""
    
    def test_is_transient_error_timeout(self):
        """Test that timeout errors are detected as transient."""
        error = Exception("Connection timeout after 30 seconds")
        assert is_transient_error(error) is True
    
    def test_is_transient_error_rate_limit(self):
        """Test that rate limit errors are detected as transient."""
        error = Exception("Rate limit exceeded, please retry after 60 seconds")
        assert is_transient_error(error) is True
    
    def test_is_transient_error_connection_reset(self):
        """Test that connection reset errors are detected as transient."""
        error = Exception("Connection reset by peer")
        assert is_transient_error(error) is True
    
    def test_is_transient_error_service_unavailable(self):
        """Test that service unavailable errors are detected as transient."""
        error = Exception("Service temporarily unavailable")
        assert is_transient_error(error) is True
    
    def test_is_transient_error_429(self):
        """Test that 429 errors are detected as transient."""
        error = Exception("HTTP 429: Too Many Requests")
        assert is_transient_error(error) is True
    
    def test_is_transient_error_503(self):
        """Test that 503 errors are detected as transient."""
        error = Exception("HTTP 503: Service Unavailable")
        assert is_transient_error(error) is True
    
    def test_is_transient_error_502(self):
        """Test that 502 errors are detected as transient."""
        error = Exception("HTTP 502: Bad Gateway")
        assert is_transient_error(error) is True
    
    def test_is_transient_error_overloaded(self):
        """Test that overloaded errors are detected as transient."""
        error = Exception("Server overloaded, please retry")
        assert is_transient_error(error) is True
    
    def test_is_transient_error_capacity(self):
        """Test that capacity errors are detected as transient."""
        error = Exception("Insufficient capacity")
        assert is_transient_error(error) is True
    
    def test_is_not_transient_error_auth(self):
        """Test that authentication errors are NOT transient."""
        error = Exception("Invalid API key")
        assert is_transient_error(error) is False
    
    def test_is_not_transient_error_not_found(self):
        """Test that not found errors are NOT transient."""
        error = Exception("Model not found: invalid-model")
        assert is_transient_error(error) is False
    
    def test_is_not_transient_error_bad_request(self):
        """Test that bad request errors are NOT transient."""
        error = Exception("Invalid request: missing required parameter")
        assert is_transient_error(error) is False
    
    def test_is_not_transient_error_permission(self):
        """Test that permission errors are NOT transient."""
        error = Exception("Permission denied")
        assert is_transient_error(error) is False
    
    def test_transient_error_patterns_list(self):
        """Test that transient error patterns are defined."""
        assert "timeout" in TRANSIENT_ERROR_PATTERNS
        assert "rate limit" in TRANSIENT_ERROR_PATTERNS
        assert "connection reset" in TRANSIENT_ERROR_PATTERNS


# ============================================================================
# Retry Logic Tests
# ============================================================================

class TestRetryLogic:
    """Tests for retry logic decorator."""
    
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        call_count = 0
        
        @with_retry(max_retries=3)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_transient_error(self):
        """Test retry succeeds after transient error."""
        call_count = 0
        
        @with_retry(max_retries=3, backoff_base=1.1)
        async def transient_then_success():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("timeout error")
            return "success"
        
        result = await transient_then_success()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test that retries are exhausted for persistent transient errors."""
        call_count = 0
        
        @with_retry(max_retries=2, backoff_base=1.1)
        async def always_transient():
            nonlocal call_count
            call_count += 1
            raise Exception("timeout error")
        
        with pytest.raises(Exception) as exc_info:
            await always_transient()
        
        assert "timeout error" in str(exc_info.value)
        assert call_count == 3  # Initial + 2 retries
    
    @pytest.mark.asyncio
    async def test_no_retry_for_non_transient(self):
        """Test that non-transient errors are not retried."""
        call_count = 0
        
        @with_retry(max_retries=3)
        async def non_transient_error():
            nonlocal call_count
            call_count += 1
            raise Exception("Invalid API key")
        
        with pytest.raises(Exception) as exc_info:
            await non_transient_error()
        
        assert "Invalid API key" in str(exc_info.value)
        assert call_count == 1  # No retries


# ============================================================================
# LLM Engine Edge Cases Tests
# ============================================================================

class TestLLMEngineEdgeCases:
    """Tests for LLM engine edge cases."""
    
    def test_engine_with_no_api_keys(self):
        """Test engine initialization with no API keys."""
        settings = MagicMock()
        settings.openai_api_key = None
        settings.anthropic_api_key = None
        settings.groq_api_key = None
        settings.deepseek_api_key = None
        settings.mistral_api_key = None
        settings.ollama_base_url = "http://localhost:11434"
        settings.default_provider = "openai"
        settings.default_model = "gpt-4o"
        settings.temperature = 0.7
        settings.max_tokens = 1000
        settings.enable_failover = True
        settings.openai_compatible_api_key = None
        settings.openai_compatible_base_url = None
        settings.openai_compatible_model = "local"
        
        engine = LLMEngine(settings)
        
        # Should still work with Ollama
        assert engine.is_configured() is False
    
    def test_engine_failover_order(self):
        """Test that failover order is correctly determined."""
        settings = LLMSettings(
            openai_api_key="sk-test",
            anthropic_api_key="sk-ant-test",
        )
        
        engine = LLMEngine(settings)
        
        # Should have multiple providers in failover order
        assert len(engine._failover_order) >= 2
        
        # Ollama should be last (always available)
        assert engine._failover_order[-1] == Provider.OLLAMA
    
    def test_provider_models_defined(self):
        """Test that all providers have models defined."""
        settings = LLMSettings(openai_api_key="sk-test")
        engine = LLMEngine(settings)
        
        for provider in Provider:
            if provider != Provider.OPENAI_COMPATIBLE:
                assert provider in engine.PROVIDER_MODELS
    
    def test_conversation_empty_to_api_format(self):
        """Test empty conversation conversion."""
        conv = Conversation()
        result = conv.to_api_format()
        assert result == []
    
    def test_conversation_large_message(self):
        """Test conversation with very large message."""
        conv = Conversation()
        large_content = "A" * 100000  # 100KB message
        
        conv.add_user(large_content)
        
        api_format = conv.to_api_format()
        assert len(api_format) == 1
        assert len(api_format[0]["content"]) == 100000
    
    def test_message_default_timestamp(self):
        """Test that message timestamp is set by default."""
        msg = Message(role="user", content="test")
        
        assert msg.timestamp is not None
        assert isinstance(msg.timestamp, datetime)
    
    def test_message_custom_metadata(self):
        """Test message with custom metadata."""
        metadata = {
            "model": "gpt-4o",
            "tokens": 100,
            "finish_reason": "stop",
        }
        msg = Message(role="assistant", content="response", metadata=metadata)
        
        assert msg.metadata["model"] == "gpt-4o"
        assert msg.metadata["tokens"] == 100


# ============================================================================
# SSRF Validation Edge Cases Tests
# ============================================================================

class TestSSRFValidationEdgeCases:
    """Tests for SSRF validation edge cases."""
    
    def test_validate_url_with_port(self):
        """Test URL with non-standard port."""
        is_valid, _ = validate_url_for_ssrf("https://example.com:8080/api")
        assert is_valid is True
    
    def test_validate_url_with_path(self):
        """Test URL with complex path."""
        is_valid, _ = validate_url_for_ssrf(
            "https://example.com/api/v1/endpoint?param=value"
        )
        assert is_valid is True
    
    def test_validate_url_with_fragment(self):
        """Test URL with fragment."""
        is_valid, _ = validate_url_for_ssrf(
            "https://example.com/page#section"
        )
        assert is_valid is True
    
    def test_validate_url_with_credentials(self):
        """Test URL with credentials."""
        is_valid, _ = validate_url_for_ssrf(
            "https://user:pass@example.com/api"
        )
        assert is_valid is True
    
    def test_validate_url_encoded_chars(self):
        """Test URL with encoded characters."""
        is_valid, _ = validate_url_for_ssrf(
            "https://example.com/path%20with%20spaces"
        )
        assert is_valid is True
    
    def test_validate_url_localhost_variations(self):
        """Test various localhost representations."""
        localhost_urls = [
            "http://localhost/admin",
            "http://127.0.0.1/admin",
            "http://[::1]/admin",
            "http://0.0.0.0/admin",
        ]
        
        for url in localhost_urls:
            is_valid, _ = validate_url_for_ssrf(url, allow_localhost=False)
            assert is_valid is False, f"Should block: {url}"
    
    def test_validate_url_private_cidr(self):
        """Test private IP ranges."""
        private_ips = [
            "http://10.0.0.1/internal",
            "http://172.16.0.1/internal",
            "http://192.168.1.1/internal",
        ]
        
        for url in private_ips:
            is_valid, _ = validate_url_for_ssrf(url, allow_localhost=False)
            assert is_valid is False, f"Should block: {url}"
    
    def test_validate_url_aws_metadata(self):
        """Test AWS metadata endpoint is blocked."""
        is_valid, _ = validate_url_for_ssrf(
            "http://169.254.169.254/latest/meta-data/",
            allow_localhost=False
        )
        assert is_valid is False
    
    def test_validate_url_empty(self):
        """Test validation of empty URL."""
        is_valid, error = validate_url_for_ssrf("")
        assert is_valid is False
        assert "empty" in error.lower()


# ============================================================================
# LLM Settings Tests
# ============================================================================

class TestLLMSettings:
    """Tests for LLM settings."""
    
    def test_llm_settings_custom(self):
        """Test LLM settings with custom values."""
        settings = LLMSettings(
            openai_api_key="sk-custom",
            temperature=0.5,
            max_tokens=2000,
            default_provider="anthropic",
            default_model="claude-sonnet-4-20250514",
        )
        
        assert settings.temperature == 0.5
        assert settings.max_tokens == 2000
        assert settings.default_provider == "anthropic"
    
    def test_llm_settings_with_api_keys(self):
        """Test LLM settings with API keys."""
        settings = LLMSettings(
            openai_api_key="sk-test",
            anthropic_api_key="sk-ant-test",
        )
        
        assert settings.openai_api_key == "sk-test"
        assert settings.anthropic_api_key == "sk-ant-test"


# ============================================================================
# Conversation Edge Cases Tests
# ============================================================================

class TestConversationEdgeCases:
    """Tests for conversation edge cases."""
    
    def test_conversation_many_messages(self):
        """Test conversation with many messages."""
        conv = Conversation()
        
        for i in range(100):
            conv.add_user(f"Message {i}")
            conv.add_assistant(f"Response {i}")
        
        assert len(conv) == 200
    
    def test_conversation_clear(self):
        """Test clearing conversation."""
        conv = Conversation()
        conv.add_user("Hello")
        conv.add_assistant("Hi")
        
        assert len(conv) == 2
        
        conv.clear()
        assert len(conv) == 0
    
    def test_conversation_system_prompt(self):
        """Test conversation with system prompt."""
        conv = Conversation(system_prompt="You are a security expert.")
        
        api_format = conv.to_api_format()
        assert api_format[0]["role"] == "system"
        assert api_format[0]["content"] == "You are a security expert."
    
    def test_conversation_mixed_roles(self):
        """Test conversation with mixed message roles."""
        conv = Conversation()
        conv.add_system("System message")
        conv.add_user("User message")
        conv.add_assistant("Assistant message")
        conv.add_user("Follow-up")
        
        roles = [msg.role for msg in conv.messages]
        assert roles == ["system", "user", "assistant", "user"]
    
    def test_get_last_no_match(self):
        """Test getting last message with no matching role."""
        conv = Conversation()
        conv.add_user("Hello")
        
        result = conv.get_last(role="assistant")
        assert result is None
    
    def test_get_last_from_empty(self):
        """Test getting last message from empty conversation."""
        conv = Conversation()
        
        result = conv.get_last()
        assert result is None
        
        result = conv.get_last(role="user")
        assert result is None


# ============================================================================
# Provider Enum Tests
# ============================================================================

class TestProviderEnum:
    """Tests for Provider enum."""
    
    def test_provider_values(self):
        """Test provider enum values."""
        assert Provider.OPENAI.value == "openai"
        assert Provider.ANTHROPIC.value == "anthropic"
        assert Provider.GROQ.value == "groq"
        assert Provider.OLLAMA.value == "ollama"
        assert Provider.DEEPSEEK.value == "deepseek"
        assert Provider.MISTRAL.value == "mistral"
    
    def test_provider_from_string(self):
        """Test creating provider from string."""
        assert Provider("openai") == Provider.OPENAI
        assert Provider("anthropic") == Provider.ANTHROPIC
        assert Provider("ollama") == Provider.OLLAMA
    
    def test_provider_all_values(self):
        """Test all provider values are unique."""
        values = [p.value for p in Provider]
        assert len(values) == len(set(values))


# ============================================================================
# Additional Security Edge Cases Tests
# ============================================================================

class TestSecurityEdgeCases:
    """Tests for additional security edge cases."""
    
    def test_ssrft_blocked_schemes(self):
        """Test that dangerous schemes are blocked."""
        blocked = [
            "file:///etc/passwd",
            "ftp://example.com/file",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
        ]
        
        for url in blocked:
            is_valid, _ = validate_url_for_ssrf(url)
            assert is_valid is False, f"Should block: {url}"
    
    def test_ssrft_allow_localhost_flag(self):
        """Test allow_localhost flag."""
        # Blocked by default
        is_valid, _ = validate_url_for_ssrf(
            "http://localhost:8080/api",
            allow_localhost=False
        )
        assert is_valid is False
        
        # Allowed with flag
        is_valid, _ = validate_url_for_ssrf(
            "http://localhost:8080/api",
            allow_localhost=True
        )
        assert is_valid is True
    
    def test_ipv6_loopback_blocked(self):
        """Test that IPv6 loopback is blocked."""
        is_valid, _ = validate_url_for_ssrf(
            "http://[::1]/admin",
            allow_localhost=False
        )
        assert is_valid is False


# ============================================================================
# Message Tests
# ============================================================================

class TestMessage:
    """Tests for Message dataclass."""
    
    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.metadata == {}
    
    def test_message_with_metadata(self):
        """Test message with metadata."""
        msg = Message(
            role="assistant",
            content="Response",
            metadata={"tokens": 50, "model": "gpt-4o"}
        )
        
        assert msg.metadata["tokens"] == 50
        assert msg.metadata["model"] == "gpt-4o"
    
    def test_message_timestamp(self):
        """Test message timestamp is set."""
        msg = Message(role="user", content="test")
        
        assert msg.timestamp is not None
        # Should be recent
        now = datetime.now(timezone.utc)
        diff = abs((now - msg.timestamp).total_seconds())
        assert diff < 5  # Within 5 seconds