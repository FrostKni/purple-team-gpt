"""Tests for the LLM Engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from purple_team_gpt.core.llm.engine import (
    Conversation,
    LLMEngine,
    Message,
    Provider,
)
from purple_team_gpt.core.llm import create_engine
from purple_team_gpt.config import LLMSettings


class TestMessage:
    """Tests for the Message dataclass."""
    
    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello world")
        assert msg.role == "user"
        assert msg.content == "Hello world"
        assert msg.metadata == {}
    
    def test_message_with_metadata(self):
        """Test creating a message with metadata."""
        msg = Message(
            role="assistant",
            content="Response",
            metadata={"model": "gpt-4o", "tokens": 100}
        )
        assert msg.metadata["model"] == "gpt-4o"
        assert msg.metadata["tokens"] == 100


class TestConversation:
    """Tests for the Conversation class."""
    
    def test_empty_conversation(self):
        """Test empty conversation."""
        conv = Conversation()
        assert len(conv) == 0
        assert conv.messages == []
    
    def test_add_user_message(self):
        """Test adding a user message."""
        conv = Conversation()
        msg = conv.add_user("Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert len(conv) == 1
    
    def test_add_assistant_message(self):
        """Test adding an assistant message."""
        conv = Conversation()
        msg = conv.add_assistant("Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"
        assert len(conv) == 1
    
    def test_add_system_message(self):
        """Test adding a system message."""
        conv = Conversation()
        msg = conv.add_system("You are helpful.")
        assert msg.role == "system"
        assert msg.content == "You are helpful."
    
    def test_to_api_format(self):
        """Test converting conversation to API format."""
        conv = Conversation()
        conv.system_prompt = "You are a security expert."
        conv.add_user("What is nmap?")
        conv.add_assistant("Nmap is a network scanning tool.")
        
        api_format = conv.to_api_format()
        assert len(api_format) == 3
        assert api_format[0]["role"] == "system"
        assert api_format[1]["role"] == "user"
        assert api_format[2]["role"] == "assistant"
    
    def test_to_api_format_no_system(self):
        """Test converting conversation without system prompt."""
        conv = Conversation()
        conv.add_user("Hello")
        
        api_format = conv.to_api_format()
        assert len(api_format) == 1
        assert api_format[0]["role"] == "user"
    
    def test_clear_conversation(self):
        """Test clearing a conversation."""
        conv = Conversation()
        conv.add_user("Hello")
        conv.add_assistant("Hi")
        assert len(conv) == 2
        
        conv.clear()
        assert len(conv) == 0
    
    def test_get_last_message(self):
        """Test getting the last message."""
        conv = Conversation()
        conv.add_user("First")
        conv.add_assistant("Second")
        
        last = conv.get_last()
        assert last.role == "assistant"
        assert last.content == "Second"
    
    def test_get_last_message_by_role(self):
        """Test getting the last message by role."""
        conv = Conversation()
        conv.add_user("User message")
        conv.add_assistant("Assistant message")
        conv.add_user("Another user message")
        
        last_assistant = conv.get_last(role="assistant")
        assert last_assistant.content == "Assistant message"
        
        last_user = conv.get_last(role="user")
        assert last_user.content == "Another user message"
    
    def test_get_last_message_empty(self):
        """Test getting last message from empty conversation."""
        conv = Conversation()
        assert conv.get_last() is None
        assert conv.get_last(role="user") is None


class TestProvider:
    """Tests for the Provider enum."""
    
    def test_provider_values(self):
        """Test provider enum values."""
        assert Provider.OPENAI.value == "openai"
        assert Provider.ANTHROPIC.value == "anthropic"
        assert Provider.GROQ.value == "groq"
        assert Provider.OLLAMA.value == "ollama"
        assert Provider.DEEPSEEK.value == "deepseek"


class TestLLMEngine:
    """Tests for the LLMEngine class."""
    
    def test_engine_initialization(self, llm_settings):
        """Test engine initialization."""
        engine = LLMEngine(llm_settings)
        assert engine.settings == llm_settings
        assert len(engine._failover_order) > 0
    
    def test_provider_models_defined(self, llm_settings):
        """Test that provider models are defined."""
        engine = LLMEngine(llm_settings)
        
        assert Provider.OPENAI in engine.PROVIDER_MODELS
        assert Provider.ANTHROPIC in engine.PROVIDER_MODELS
        assert "gpt-4o" in engine.PROVIDER_MODELS[Provider.OPENAI]
    
    def test_get_failover_order(self, llm_settings):
        """Test failover order is set correctly."""
        engine = LLMEngine(llm_settings)
        
        # Should include OpenAI since we have an API key
        assert Provider.OPENAI in engine._failover_order
        # Ollama should always be last (no API key required)
        assert Provider.OLLAMA in engine._failover_order
    
    def test_get_model_string(self, llm_settings):
        """Test model string conversion."""
        engine = LLMEngine(llm_settings)
        
        assert engine._get_model_string(Provider.OPENAI, "gpt-4o") == "openai/gpt-4o"
        assert engine._get_model_string(Provider.ANTHROPIC, "claude-sonnet") == "anthropic/claude-sonnet"
        assert engine._get_model_string(Provider.OLLAMA, "llama3") == "ollama/llama3"
    
    def test_get_default_model_for_provider(self, llm_settings):
        """Test getting default model for provider."""
        engine = LLMEngine(llm_settings)
        
        default_openai = engine._get_default_model_for_provider(Provider.OPENAI)
        assert default_openai in engine.PROVIDER_MODELS[Provider.OPENAI]
    
    def test_is_configured_true(self, llm_settings):
        """Test is_configured returns True with API key."""
        engine = LLMEngine(llm_settings)
        assert engine.is_configured() is True
    
    def test_is_configured_false(self):
        """Test is_configured returns False without API keys."""
        settings = MagicMock()
        settings.openai_api_key = None
        settings.anthropic_api_key = None
        settings.groq_api_key = None
        settings.deepseek_api_key = None
        settings.mistral_api_key = None
        settings.openai_compatible_base_url = None
        settings.openai_compatible_api_key = None
        settings.openai_compatible_model = "local"
        settings.ollama_base_url = "http://localhost:11434"
        settings.default_provider = "openai"
        settings.default_model = "gpt-4o"
        settings.temperature = 0.7
        settings.max_tokens = 4096
        settings.enable_failover = True
        engine = LLMEngine(settings)
        assert engine.is_configured() is False
    
    def test_get_available_providers(self, llm_settings):
        """Test getting available providers."""
        engine = LLMEngine(llm_settings)
        providers = engine.get_available_providers()
        
        assert isinstance(providers, list)
        assert len(providers) > 0
        # Ollama should always be available
        assert Provider.OLLAMA in providers
    
    def test_get_available_models(self, llm_settings):
        """Test getting available models for a provider."""
        engine = LLMEngine(llm_settings)
        models = engine.get_available_models(Provider.OPENAI)
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-4o" in models
    
    @pytest.mark.asyncio
    async def test_count_tokens(self, llm_settings):
        """Test token counting (approximate)."""
        engine = LLMEngine(llm_settings)
        
        text = "Hello world, this is a test."
        count = await engine.count_tokens(text)
        
        # Approximate: ~4 chars per token
        expected = len(text) // 4
        assert count == expected
    
    @pytest.mark.asyncio
    async def test_quick_ask_blocking(self, llm_settings, mock_litellm_response):
        """Test quick_ask with blocking response."""
        with patch("purple_team_gpt.core.llm.engine.acompletion", new_callable=AsyncMock) as mock_acomp:
            mock_acomp.return_value = mock_litellm_response
            
            engine = LLMEngine(llm_settings)
            response = await engine.quick_ask("What is nmap?", stream=False)
            
            assert response == "This is a test response from the LLM."
            mock_acomp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_quick_ask_with_system(self, llm_settings, mock_litellm_response):
        """Test quick_ask with system prompt."""
        with patch("purple_team_gpt.core.llm.engine.acompletion", new_callable=AsyncMock) as mock_acomp:
            mock_acomp.return_value = mock_litellm_response
            
            engine = LLMEngine(llm_settings)
            response = await engine.quick_ask(
                "What is nmap?",
                system="You are a security expert.",
                stream=False
            )
            
            # Check that system message was included
            call_args = mock_acomp.call_args
            messages = call_args.kwargs.get("messages", call_args[0][0] if call_args[0] else [])
            assert any(m["role"] == "system" for m in messages)
    
    @pytest.mark.asyncio
    async def test_chat_blocking(self, llm_settings, mock_litellm_response):
        """Test chat with blocking response."""
        with patch("purple_team_gpt.core.llm.engine.acompletion", new_callable=AsyncMock) as mock_acomp:
            mock_acomp.return_value = mock_litellm_response
            
            engine = LLMEngine(llm_settings)
            conv = Conversation()
            conv.add_user("Hello")
            
            response = await engine.chat(conv, stream=False)
            assert response == "This is a test response from the LLM."
    
    @pytest.mark.asyncio
    async def test_chat_with_specific_provider(self, llm_settings, mock_litellm_response):
        """Test chat with specific provider."""
        with patch("purple_team_gpt.core.llm.engine.acompletion", new_callable=AsyncMock) as mock_acomp:
            mock_acomp.return_value = mock_litellm_response
            
            engine = LLMEngine(llm_settings)
            conv = Conversation()
            conv.add_user("Hello")
            
            await engine.chat(conv, stream=False, provider=Provider.OPENAI)
            
            # Check that model string starts with openai/
            call_args = mock_acomp.call_args
            model = call_args.kwargs.get("model", "")
            assert model.startswith("openai/")
    
    @pytest.mark.asyncio
    async def test_chat_failover(self):
        """Test that chat fails over to next provider on error."""
        settings = LLMSettings(
            openai_api_key="test-key",
            anthropic_api_key="test-key",
        )
        
        call_count = 0
        
        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("OpenAI failed")
            
            mock_choice = MagicMock()
            mock_choice.message.content = "Success from Anthropic"
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            return mock_response
        
        with patch("purple_team_gpt.core.llm.engine.acompletion", new_callable=AsyncMock) as mock_acomp:
            mock_acomp.side_effect = mock_acompletion
            
            engine = LLMEngine(settings)
            conv = Conversation()
            conv.add_user("Hello")
            
            response = await engine.chat(conv, stream=False)
            assert response == "Success from Anthropic"
            assert call_count == 2  # First failed, second succeeded
    
    @pytest.mark.asyncio
    async def test_chat_all_providers_fail(self):
        """Test that chat raises error when all providers fail."""
        settings = LLMSettings()  # No API keys, only Ollama
        
        with patch("purple_team_gpt.core.llm.engine.acompletion", new_callable=AsyncMock) as mock_acomp:
            mock_acomp.side_effect = Exception("Connection failed")
            
            engine = LLMEngine(settings)
            conv = Conversation()
            conv.add_user("Hello")
            
            with pytest.raises(RuntimeError, match="All LLM providers failed"):
                await engine.chat(conv, stream=False)


class TestCreateEngine:
    """Tests for the create_engine factory function."""
    
    def test_create_engine_with_settings(self, llm_settings):
        """Test creating engine with provided settings."""
        engine = create_engine(llm_settings)
        assert engine.settings == llm_settings
    
    def test_create_engine_without_settings(self):
        """Test creating engine with default settings."""
        with patch("purple_team_gpt.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.llm = LLMSettings()
            mock_get_settings.return_value = mock_settings
            
            engine = create_engine()
            assert isinstance(engine, LLMEngine)