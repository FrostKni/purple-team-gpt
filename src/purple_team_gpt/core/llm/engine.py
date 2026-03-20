"""Multi-provider LLM engine with LiteLLM and OpenAI-compatible support."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

import litellm
from litellm import acompletion

from purple_team_gpt.config import LLMSettings, OpenAICompatibleEndpoint

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.drop_params = True


class Provider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass
class Message:
    """Chat message."""
    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Conversation container for managing chat history."""
    messages: List[Message] = field(default_factory=list)
    system_prompt: str = ""

    def add(self, role: str, content: str, **metadata: Any) -> Message:
        """Add a message to the conversation."""
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        return msg

    def add_user(self, content: str, **metadata: Any) -> Message:
        """Add a user message."""
        return self.add("user", content, **metadata)

    def add_assistant(self, content: str, **metadata: Any) -> Message:
        """Add an assistant message."""
        return self.add("assistant", content, **metadata)

    def add_system(self, content: str, **metadata: Any) -> Message:
        """Add a system message."""
        return self.add("system", content, **metadata)

    def to_api_format(self) -> List[Dict[str, str]]:
        """Convert to LiteLLM/OpenAI API format."""
        result = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def get_last(self, role: Optional[str] = None) -> Optional[Message]:
        """Get the last message, optionally filtered by role."""
        if role:
            for msg in reversed(self.messages):
                if msg.role == role:
                    return msg
            return None
        return self.messages[-1] if self.messages else None

    def __len__(self) -> int:
        return len(self.messages)


@dataclass
class ProviderConfig:
    """Configuration for a specific provider."""
    provider: Provider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    extra_kwargs: Dict[str, Any] = field(default_factory=dict)


class LLMEngine:
    """Multi-provider LLM engine with automatic failover and OpenAI-compatible support."""

    PROVIDER_MODELS = {
        Provider.OPENAI: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1", "o1-mini", "o3-mini"],
        Provider.ANTHROPIC: ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
        Provider.GROQ: ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
        Provider.OLLAMA: ["llama3.2", "llama3.1", "mistral", "codellama", "qwen2.5"],
        Provider.DEEPSEEK: ["deepseek-chat", "deepseek-reasoner"],
        Provider.MISTRAL: ["mistral-large-latest", "mistral-medium-latest", "codestral-latest"],
        Provider.OPENAI_COMPATIBLE: [],  # Models are defined per-endpoint
    }

    def __init__(
        self, 
        settings: LLMSettings,
        openai_compatible_endpoints: Optional[List[OpenAICompatibleEndpoint]] = None,
    ):
        """Initialize the LLM engine with settings.
        
        Args:
            settings: LLM configuration settings
            openai_compatible_endpoints: List of OpenAI-compatible endpoint configurations
        """
        self.settings = settings
        self.openai_compatible_endpoints = openai_compatible_endpoints or []
        self._setup_api_keys()
        self._failover_order = self._get_failover_order()
        self._provider_configs = self._build_provider_configs()

    def _setup_api_keys(self) -> None:
        """Set API keys from settings for LiteLLM."""
        import os
        if self.settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key
        if self.settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.anthropic_api_key
        if self.settings.groq_api_key:
            os.environ["GROQ_API_KEY"] = self.settings.groq_api_key
        if self.settings.deepseek_api_key:
            os.environ["DEEPSEEK_API_KEY"] = self.settings.deepseek_api_key
        if hasattr(self.settings, 'mistral_api_key') and self.settings.mistral_api_key:
            os.environ["MISTRAL_API_KEY"] = self.settings.mistral_api_key
        if self.settings.ollama_base_url:
            os.environ["OLLAMA_API_BASE"] = self.settings.ollama_base_url

    def _get_failover_order(self) -> List[Union[Provider, str]]:
        """Get provider failover order based on available API keys.
        
        Returns:
            List of providers (or endpoint names for OpenAI-compatible)
        """
        order = []
        
        # Add OpenAI-compatible endpoints first (highest priority for local setups)
        for endpoint in self.openai_compatible_endpoints:
            if endpoint.enabled:
                order.append(f"openai_compatible:{endpoint.name}")
        
        # Also check for env-configured OpenAI-compatible
        if self.settings.openai_compatible_base_url:
            if "openai_compatible:env_configured" not in order:
                order.append("openai_compatible:env_configured")
        
        # Add standard providers with configured API keys
        if self.settings.openai_api_key:
            order.append(Provider.OPENAI)
        if self.settings.anthropic_api_key:
            order.append(Provider.ANTHROPIC)
        if self.settings.groq_api_key:
            order.append(Provider.GROQ)
        if self.settings.deepseek_api_key:
            order.append(Provider.DEEPSEEK)
        if self.settings.mistral_api_key:
            order.append(Provider.MISTRAL)
        
        # Ollama is always available locally (no API key required)
        order.append(Provider.OLLAMA)
        
        return order

    def _build_provider_configs(self) -> Dict[str, ProviderConfig]:
        """Build provider configurations for each failover option."""
        configs = {}
        
        # Standard providers
        if self.settings.openai_api_key:
            configs[Provider.OPENAI.value] = ProviderConfig(
                provider=Provider.OPENAI,
                model=self.settings.default_model,
                api_key=self.settings.openai_api_key,
            )
        
        if self.settings.anthropic_api_key:
            configs[Provider.ANTHROPIC.value] = ProviderConfig(
                provider=Provider.ANTHROPIC,
                model=self.settings.default_model,
                api_key=self.settings.anthropic_api_key,
            )
        
        if self.settings.groq_api_key:
            configs[Provider.GROQ.value] = ProviderConfig(
                provider=Provider.GROQ,
                model="llama-3.3-70b-versatile",
                api_key=self.settings.groq_api_key,
            )
        
        if self.settings.deepseek_api_key:
            configs[Provider.DEEPSEEK.value] = ProviderConfig(
                provider=Provider.DEEPSEEK,
                model="deepseek-chat",
                api_key=self.settings.deepseek_api_key,
            )
        
        if self.settings.mistral_api_key:
            configs[Provider.MISTRAL.value] = ProviderConfig(
                provider=Provider.MISTRAL,
                model="mistral-large-latest",
                api_key=self.settings.mistral_api_key,
            )
        
        configs[Provider.OLLAMA.value] = ProviderConfig(
            provider=Provider.OLLAMA,
            model="llama3.2",
            base_url=self.settings.ollama_base_url,
        )
        
        # OpenAI-compatible endpoints
        for endpoint in self.openai_compatible_endpoints:
            if endpoint.enabled:
                key = f"openai_compatible:{endpoint.name}"
                configs[key] = ProviderConfig(
                    provider=Provider.OPENAI_COMPATIBLE,
                    model=endpoint.model,
                    api_key=endpoint.api_key or "local",
                    base_url=endpoint.base_url,
                    extra_kwargs={
                        "timeout": endpoint.timeout,
                        "headers": endpoint.headers,
                    },
                )
        
        # Env-configured OpenAI-compatible
        if self.settings.openai_compatible_base_url:
            key = "openai_compatible:env_configured"
            configs[key] = ProviderConfig(
                provider=Provider.OPENAI_COMPATIBLE,
                model=self.settings.openai_compatible_model,
                api_key=self.settings.openai_compatible_api_key or "local",
                base_url=self.settings.openai_compatible_base_url,
            )
        
        return configs

    def _get_model_string(
        self, 
        provider: Union[Provider, str], 
        model: str,
        base_url: Optional[str] = None,
    ) -> str:
        """Convert to LiteLLM model string format.
        
        For OpenAI-compatible endpoints, we use openai/<model> with base_url.
        """
        if isinstance(provider, str) and provider.startswith("openai_compatible"):
            # OpenAI-compatible uses openai/ prefix with custom base_url
            return f"openai/{model}"
        
        prefix_map = {
            Provider.OPENAI: "openai/",
            Provider.ANTHROPIC: "anthropic/",
            Provider.GROQ: "groq/",
            Provider.OLLAMA: "ollama/",
            Provider.DEEPSEEK: "deepseek/",
            Provider.MISTRAL: "mistral/",
        }
        
        return f"{prefix_map.get(provider, 'openai/')}{model}"

    def _get_default_model_for_provider(self, provider: Union[Provider, str]) -> str:
        """Get the default model for a provider."""
        if isinstance(provider, str) and provider.startswith("openai_compatible"):
            # Get from endpoint config
            config = self._provider_configs.get(provider)
            return config.model if config else self.settings.default_model
        
        models = self.PROVIDER_MODELS.get(provider, [])
        return models[0] if models else self.settings.default_model

    async def chat(
        self,
        conversation: Conversation,
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
        model: Optional[str] = None,
        provider: Optional[Union[Provider, str]] = None,
    ) -> str:
        """
        Send conversation to LLM and return response.
        
        Args:
            conversation: The conversation to send
            stream: Whether to stream the response
            on_token: Callback for each token when streaming
            model: Specific model to use (optional)
            provider: Specific provider to use (optional)
            
        Returns:
            The LLM response as a string
        """
        messages = conversation.to_api_format()
        
        # Determine which providers to try
        if provider:
            providers_to_try = [provider]
        elif self.settings.enable_failover:
            providers_to_try = self._failover_order
        else:
            providers_to_try = [self._failover_order[0]] if self._failover_order else []
        
        last_error = None
        
        for prov in providers_to_try:
            try:
                config = self._provider_configs.get(prov if isinstance(prov, str) else prov.value)
                if not config:
                    # Handle standard provider without explicit config
                    if isinstance(prov, Provider):
                        config = ProviderConfig(provider=prov, model=self.settings.default_model)
                    else:
                        logger.warning(f"No config found for provider: {prov}")
                        continue
                
                # Use specified model or config default
                model_name = model or config.model or self.settings.default_model
                model_string = self._get_model_string(prov, model_name, config.base_url)
                
                logger.debug(f"Trying provider {prov} with model {model_string}")
                
                # Build completion kwargs
                completion_kwargs = {
                    "model": model_string,
                    "messages": messages,
                    "temperature": self.settings.temperature,
                    "max_tokens": self.settings.max_tokens,
                }
                
                # Add base_url for OpenAI-compatible endpoints
                if config.base_url:
                    completion_kwargs["api_base"] = config.base_url
                
                # Add any extra kwargs
                if config.extra_kwargs:
                    for key, value in config.extra_kwargs.items():
                        if key not in ["headers"]:  # Skip headers for now
                            completion_kwargs[key] = value
                
                if stream and on_token:
                    return await self._stream_chat(completion_kwargs, on_token)
                else:
                    return await self._blocking_chat(completion_kwargs)

            except Exception as e:
                last_error = e
                logger.warning(f"Provider {prov} failed: {e}")
                continue

        error_msg = f"All LLM providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def _blocking_chat(self, kwargs: Dict[str, Any]) -> str:
        """Non-streaming chat completion."""
        response = await acompletion(**kwargs)
        return response.choices[0].message.content or ""

    async def _stream_chat(
        self,
        kwargs: Dict[str, Any],
        on_token: Callable[[str], None],
    ) -> str:
        """Streaming chat completion."""
        kwargs["stream"] = True
        response = await acompletion(**kwargs)

        full_response = []
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response.append(token)
                on_token(token)

        return "".join(full_response)

    async def stream(
        self,
        conversation: Conversation,
        model: Optional[str] = None,
        provider: Optional[Union[Provider, str]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response from LLM as an async iterator.
        
        Args:
            conversation: The conversation to send
            model: Specific model to use (optional)
            provider: Specific provider to use (optional)
            
        Yields:
            Tokens from the LLM response
        """
        messages = conversation.to_api_format()
        
        providers_to_try = [provider] if provider else self._failover_order
        
        for prov in providers_to_try:
            try:
                config = self._provider_configs.get(prov if isinstance(prov, str) else prov.value)
                if not config:
                    if isinstance(prov, Provider):
                        config = ProviderConfig(provider=prov, model=self.settings.default_model)
                    else:
                        continue
                
                model_name = model or config.model or self.settings.default_model
                model_string = self._get_model_string(prov, model_name, config.base_url)
                
                completion_kwargs = {
                    "model": model_string,
                    "messages": messages,
                    "temperature": self.settings.temperature,
                    "max_tokens": self.settings.max_tokens,
                    "stream": True,
                }
                
                if config.base_url:
                    completion_kwargs["api_base"] = config.base_url

                response = await acompletion(**completion_kwargs)

                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return

            except Exception as e:
                logger.warning(f"Provider {prov} failed: {e}")
                continue

        raise RuntimeError("All LLM providers failed")

    async def quick_ask(
        self,
        prompt: str,
        system: str = "",
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        One-shot question without conversation history.
        
        Args:
            prompt: The user prompt
            system: System prompt (optional)
            stream: Whether to stream the response
            on_token: Callback for streaming
            
        Returns:
            The LLM response
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Use first available provider
        if not self._failover_order:
            raise RuntimeError("No LLM providers configured")

        provider = self._failover_order[0]
        config = self._provider_configs.get(provider if isinstance(provider, str) else provider.value)
        
        if not config:
            config = ProviderConfig(
                provider=Provider.OPENAI if isinstance(provider, Provider) else Provider.OPENAI_COMPATIBLE,
                model=self.settings.default_model,
            )
        
        completion_kwargs = {
            "model": self._get_model_string(provider, config.model or self.settings.default_model, config.base_url),
            "messages": messages,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }
        
        if config.base_url:
            completion_kwargs["api_base"] = config.base_url

        if stream and on_token:
            return await self._stream_chat(completion_kwargs, on_token)
        return await self._blocking_chat(completion_kwargs)

    @property
    def available_providers(self) -> List[str]:
        """List of available provider names."""
        return [str(p) for p in self._failover_order]

    @property
    def primary_provider(self) -> Optional[str]:
        """The primary (first) provider in failover order."""
        return str(self._failover_order[0]) if self._failover_order else None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all configured providers.
        
        Returns:
            Dictionary with provider health status
        """
        results = {}
        
        for provider in self._failover_order:
            try:
                config = self._provider_configs.get(
                    provider if isinstance(provider, str) else provider.value
                )
                if not config:
                    results[str(provider)] = {"status": "not_configured", "error": "No config"}
                    continue
                
                # Quick test with minimal tokens
                test_kwargs = {
                    "model": self._get_model_string(provider, config.model or "gpt-3.5-turbo", config.base_url),
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                }
                
                if config.base_url:
                    test_kwargs["api_base"] = config.base_url
                
                await acompletion(**test_kwargs)
                results[str(provider)] = {"status": "healthy"}
                
            except Exception as e:
                results[str(provider)] = {"status": "unhealthy", "error": str(e)}
        
        return results

    def get_provider_models(self, provider: Union[Provider, str]) -> List[str]:
        """Get available models for a provider."""
        if isinstance(provider, str) and provider.startswith("openai_compatible"):
            config = self._provider_configs.get(provider)
            return [config.model] if config and config.model else []
        
        if isinstance(provider, Provider):
            return self.PROVIDER_MODELS.get(provider, [])
        
        return []

    def add_openai_compatible_endpoint(self, endpoint: OpenAICompatibleEndpoint) -> None:
        """Add a new OpenAI-compatible endpoint at runtime."""
        self.openai_compatible_endpoints.append(endpoint)
        self._failover_order = self._get_failover_order()
        self._provider_configs = self._build_provider_configs()

    def remove_openai_compatible_endpoint(self, name: str) -> bool:
        """Remove an OpenAI-compatible endpoint by name."""
        original_count = len(self.openai_compatible_endpoints)
        self.openai_compatible_endpoints = [
            ep for ep in self.openai_compatible_endpoints if ep.name != name
        ]
        if len(self.openai_compatible_endpoints) < original_count:
            self._failover_order = self._get_failover_order()
            self._provider_configs = self._build_provider_configs()
            return True
        return False

    def get_available_providers(self) -> List[Union[Provider, str]]:
        """Get list of available providers."""
        return self._failover_order

    def get_available_models(self, provider: Union[Provider, str]) -> List[str]:
        """Get available models for a provider (alias for get_provider_models)."""
        return self.get_provider_models(provider)

    def is_configured(self) -> bool:
        """Check if at least one provider with an API key is configured."""
        return any(
            bool(config.api_key and config.api_key != "local")
            for config in self._provider_configs.values()
        )

    async def count_tokens(self, text: str) -> int:
        """Approximate token count for text.
        
        Uses a simple approximation of ~4 characters per token.
        For accurate counts, use tiktoken or the model's tokenizer.
        """
        return len(text) // 4