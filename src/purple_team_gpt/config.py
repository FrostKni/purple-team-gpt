"""Configuration management using pydantic-settings."""

import os
import re
from functools import lru_cache
from typing import Literal, Optional, List, Set
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# SSRF Prevention: Allowed URL schemes and blocked IP ranges
ALLOWED_URL_SCHEMES: Set[str] = {"http", "https"}
BLOCKED_PRIVATE_IP_PATTERNS = [
    r"^127\.",  # Loopback
    r"^10\.",  # Class A private
    r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",  # Class B private
    r"^192\.168\.",  # Class C private
    r"^169\.254\.",  # Link-local
    r"^0\.0\.0\.0",  # All interfaces
    r"^::1",  # IPv6 loopback
    r"^fc00:",  # IPv6 private
    r"^fe80:",  # IPv6 link-local
    r"^localhost$",  # Localhost hostname
]


def validate_url_for_ssrf(url: str, allow_localhost: bool = False) -> tuple[bool, str]:
    """Validate a URL to prevent SSRF attacks.

    Args:
        url: The URL to validate
        allow_localhost: Whether to allow localhost/private IPs (for local development)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"

    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
            return (
                False,
                f"URL scheme '{parsed.scheme}' not allowed. Allowed: {ALLOWED_URL_SCHEMES}",
            )

        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            return False, "Could not parse hostname from URL"

        # Check for blocked IP patterns if not allowing localhost
        if not allow_localhost:
            hostname_lower = hostname.lower()
            for pattern in BLOCKED_PRIVATE_IP_PATTERNS:
                if re.match(pattern, hostname_lower):
                    return False, f"Access to private/internal addresses is blocked: {hostname}"

        return True, ""

    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"


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

    # SSRF protection
    allow_localhost: bool = True  # Allow localhost for local development

    @model_validator(mode="after")
    def validate_base_url(self) -> "OpenAICompatibleEndpoint":
        """Validate base_url for SSRF prevention."""
        if self.enabled and self.base_url:
            # For configuration, we allow localhost if explicitly set
            is_valid, error = validate_url_for_ssrf(
                self.base_url, allow_localhost=self.allow_localhost
            )
            if not is_valid:
                raise ValueError(f"Invalid base_url: {error}")
        return self


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    # Standard provider API keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
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
        "openai",
        "anthropic",
        "groq",
        "gemini",
        "ollama",
        "deepseek",
        "mistral",
        "openai_compatible",
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
    secret_key: Optional[str] = None  # REQUIRED - no default for security

    # JWT settings
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: Optional[str]) -> str:
        if not v:
            # In production, this should fail. For development, generate a warning.
            import secrets as sec
            import warnings

            warnings.warn(
                "APP_SECRET_KEY is not set. Using a temporary insecure key. "
                "Set APP_SECRET_KEY environment variable for production. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"',
                UserWarning,
            )
            return sec.token_hex(32)  # Generate temporary key for development
        if len(v) < 32:
            raise ValueError("APP_SECRET_KEY must be at least 32 characters long")
        return v

    host: str = "0.0.0.0"
    port: int = 8000


class AgentSettings(BaseSettings):
    """Agent configuration."""

    model_config = SettingsConfigDict(env_prefix="AGENT_")

    max_steps: int = 50
    timeout: int = 300
    safe_mode: bool = True
    auto_confirm: bool = False


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="DB_")

    direct_url: Optional[str] = (
        None  # Direct DATABASE_URL override (e.g., sqlite+aiosqlite:///./data/app.db)
    )
    host: str = "localhost"
    port: int = 5432
    name: str = "purple_team_gpt"
    user: str = "postgres"
    password: str = "postgres"

    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30

    @property
    def url(self) -> str:
        """Get the database URL."""
        if self.direct_url:
            return self.direct_url
        return f"postgresql://{self.user}:***@{self.host}:{self.port}/{self.name}"

    @property
    def async_url(self) -> str:
        """Get the async database URL."""
        if self.direct_url:
            # Convert sqlite:// to sqlite+aiosqlite:// if needed
            if self.direct_url.startswith("sqlite://") and "+aiosqlite" not in self.direct_url:
                return self.direct_url.replace("sqlite://", "sqlite+aiosqlite://")
            return self.direct_url
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )


class Settings(BaseSettings):
    """Main settings container."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)

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
