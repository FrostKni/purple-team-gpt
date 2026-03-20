"""Configuration management using pydantic-settings."""

from functools import lru_cache
from typing import Literal, Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAICompatibleEndpoint(BaseSettings):
    """Configuration for an OpenAI-compatible endpoint.
    
    Supports services like:
    - OpenRouter (https://openrouter.ai/api/v1)
    - LocalAI (http://localhost:8080/v1)
    - vLLM (http://localhost:8000/v1)
    - LMStudio (http://localhost:1234/v1)
    - Ollama OpenAI-compatible (http://localhost:11434/v1)
    - Together AI (https://api.together.xyz/v1)
    - Azure OpenAI (https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT)
    - Custom OpenAI-compatible servers
    """
    
    model_config = SettingsConfigDict(env_prefix="OPENAI_COMPAT_")
    
    name: str = "default"  # Friendly name for this endpoint
    api_key: Optional[str] = None  # API key (can be any string for local servers)
    base_url: str = "http://localhost:11434/v1"  # Base URL for the API
    model: str = "llama3.2"  # Default model to use
    enabled: bool = True  # Whether this endpoint is enabled
    
    # Advanced options
    timeout: int = 300  # Request timeout in seconds
    max_retries: int = 3  # Max retry attempts
    headers: dict = Field(default_factory=dict)  # Additional headers


class LLMSettings(BaseSettings):
    """LLM provider configuration."""
    
    model_config = SettingsConfigDict(env_prefix="LLM_")
    
    # Standard provider API keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    
    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    
    # OpenAI-compatible endpoint (single endpoint via env vars)
    openai_compatible_api_key: Optional[str] = None
    openai_compatible_base_url: Optional[str] = None
    openai_compatible_model: str = "local-model"
    
    # Default provider selection
    default_provider: Literal[
        "openai", "anthropic", "groq", "ollama", "deepseek", 
        "mistral", "openai_compatible"
    ] = "openai"
    default_model: str = "gpt-4o"
    
    # Generation parameters
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    
    # Failover settings
    enable_failover: bool = True  # Enable automatic failover between providers
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v
    
    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_tokens must be positive")
        return v


class ChromaSettings(BaseSettings):
    """ChromaDB configuration."""
    
    model_config = SettingsConfigDict(env_prefix="CHROMA_")
    
    host: str = "localhost"
    port: int = 8001
    persist_dir: str = "./data/chromadb"


class AppSettings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(env_prefix="APP_")
    
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    host: str = "0.0.0.0"
    port: int = 8000


class AgentSettings(BaseSettings):
    """Agent configuration."""
    
    model_config = SettingsConfigDict(env_prefix="AGENT_")
    
    max_steps: int = 50
    timeout: int = 300
    safe_mode: bool = True
    auto_confirm: bool = False


class Settings(BaseSettings):
    """Main settings container."""
    
    llm: LLMSettings = Field(default_factory=LLMSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    
    # Multiple OpenAI-compatible endpoints (configured programmatically)
    openai_compatible_endpoints: List[OpenAICompatibleEndpoint] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    
    # Add OpenAI-compatible endpoint from env vars if configured
    if settings.llm.openai_compatible_base_url:
        endpoint = OpenAICompatibleEndpoint(
            name="env_configured",
            api_key=settings.llm.openai_compatible_api_key,
            base_url=settings.llm.openai_compatible_base_url,
            model=settings.llm.openai_compatible_model,
        )
        settings.openai_compatible_endpoints.append(endpoint)
    
    return settings