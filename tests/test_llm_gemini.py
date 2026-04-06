"""Tests for Gemini LLM provider integration."""

import pytest
from purple_team_gpt.config import LLMSettings
from purple_team_gpt.core.llm.engine import LLMEngine, Provider


class TestGeminiProvider:
    """Test Gemini provider integration."""

    def test_gemini_in_provider_enum(self):
        """Test that GEMINI is in the Provider enum."""
        assert hasattr(Provider, "GEMINI")
        assert Provider.GEMINI.value == "gemini"

    def test_gemini_in_failover_order(self):
        """Test that Gemini appears in failover order when API key is set."""
        settings = LLMSettings(gemini_api_key="test-gemini-key")
        engine = LLMEngine(settings)

        # Gemini should be in failover order
        assert Provider.GEMINI in engine._failover_order

    def test_gemini_not_in_failover_order_without_key(self):
        """Test that Gemini is not in failover order when no API key is set."""
        settings = LLMSettings()
        engine = LLMEngine(settings)

        # Gemini should not be in failover order without API key
        assert Provider.GEMINI not in engine._failover_order

    def test_gemini_model_string(self):
        """Test that Gemini model strings are formatted correctly for LiteLLM."""
        engine = LLMEngine(LLMSettings())
        model_string = engine._get_model_string(Provider.GEMINI, "gemini-2.0-flash")

        assert model_string == "gemini/gemini-2.0-flash"

    def test_gemini_models_defined(self):
        """Test that Gemini models are defined in PROVIDER_MODELS."""
        engine = LLMEngine(LLMSettings())
        models = engine.get_provider_models(Provider.GEMINI)

        assert "gemini-2.0-flash" in models
        assert "gemini-1.5-pro" in models
        assert "gemini-1.5-flash" in models

    def test_gemini_failover_position_after_groq(self):
        """Test that Gemini is positioned after Groq in failover order."""
        settings = LLMSettings(
            groq_api_key="test-groq-key",
            gemini_api_key="test-gemini-key",
            deepseek_api_key="test-deepseek-key",
        )
        engine = LLMEngine(settings)

        # Get indices of each provider
        groq_idx = engine._failover_order.index(Provider.GROQ)
        gemini_idx = engine._failover_order.index(Provider.GEMINI)
        deepseek_idx = engine._failover_order.index(Provider.DEEPSEEK)

        # Gemini should be after Groq, before DeepSeek
        assert gemini_idx > groq_idx, "Gemini should be after Groq"
        assert gemini_idx < deepseek_idx, "Gemini should be before DeepSeek"

    def test_gemini_in_default_provider_literal(self):
        """Test that gemini is an accepted default_provider value."""
        # This should not raise an error
        settings = LLMSettings(default_provider="gemini")
        assert settings.default_provider == "gemini"

    def test_gemini_provider_config_built(self):
        """Test that ProviderConfig is built for Gemini when API key exists."""
        settings = LLMSettings(gemini_api_key="test-gemini-key")
        engine = LLMEngine(settings)

        config = engine._provider_configs.get(Provider.GEMINI.value)
        assert config is not None
        assert config.provider == Provider.GEMINI
        assert config.model == "gemini-2.0-flash"
        assert config.api_key == "test-gemini-key"

    def test_gemini_api_key_set_in_environment(self, monkeypatch):
        """Test that GEMINI_API_KEY is set in environment when configured."""
        settings = LLMSettings(gemini_api_key="test-gemini-key")
        engine = LLMEngine(settings)

        import os

        assert os.environ.get("GEMINI_API_KEY") == "test-gemini-key"
