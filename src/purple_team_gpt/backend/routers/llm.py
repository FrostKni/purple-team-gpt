"""LLM provider management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from purple_team_gpt.config import OpenAICompatibleEndpoint
from purple_team_gpt.core.llm.engine import LLMEngine

router = APIRouter()

# Will be set by main.py during lifespan
_llm_engine: Optional[LLMEngine] = None


def set_llm_engine(engine: LLMEngine) -> None:
    """Set the LLM engine instance."""
    global _llm_engine
    _llm_engine = engine


class EndpointCreate(BaseModel):
    """Request model for creating an OpenAI-compatible endpoint."""
    name: str = Field(..., description="Friendly name for this endpoint")
    api_key: Optional[str] = Field(None, description="API key (can be any string for local servers)")
    base_url: str = Field(..., description="Base URL for the OpenAI-compatible API")
    model: str = Field(..., description="Default model to use")
    enabled: bool = Field(True, description="Whether this endpoint is enabled")
    timeout: int = Field(300, description="Request timeout in seconds")


class EndpointResponse(BaseModel):
    """Response model for an endpoint."""
    name: str
    base_url: str
    model: str
    enabled: bool
    timeout: int


class ProviderInfo(BaseModel):
    """Information about a provider."""
    name: str
    models: List[str]


@router.get("/providers", response_model=List[ProviderInfo])
async def list_providers():
    """List all available LLM providers and their models."""
    if not _llm_engine:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    
    providers = []
    for provider_name in _llm_engine.get_available_providers():
        models = _llm_engine.get_available_models(provider_name)
        providers.append(ProviderInfo(name=provider_name, models=models))
    
    return providers


@router.get("/endpoints", response_model=List[EndpointResponse])
async def list_endpoints():
    """List all configured OpenAI-compatible endpoints."""
    if not _llm_engine:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    
    return [
        EndpointResponse(
            name=ep.name,
            base_url=ep.base_url,
            model=ep.model,
            enabled=ep.enabled,
            timeout=ep.timeout,
        )
        for ep in _llm_engine.openai_compatible_endpoints
    ]


@router.post("/endpoints", response_model=EndpointResponse, status_code=201)
async def add_endpoint(data: EndpointCreate):
    """Add a new OpenAI-compatible endpoint.
    
    This allows dynamically adding endpoints like:
    - OpenRouter: https://openrouter.ai/api/v1
    - LocalAI: http://localhost:8080/v1
    - vLLM: http://localhost:8000/v1
    - LMStudio: http://localhost:1234/v1
    - Any OpenAI-compatible server
    """
    if not _llm_engine:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    
    # Check if endpoint with same name exists
    for ep in _llm_engine.openai_compatible_endpoints:
        if ep.name == data.name:
            raise HTTPException(
                status_code=400, 
                detail=f"Endpoint with name '{data.name}' already exists"
            )
    
    endpoint = OpenAICompatibleEndpoint(
        name=data.name,
        api_key=data.api_key,
        base_url=data.base_url,
        model=data.model,
        enabled=data.enabled,
        timeout=data.timeout,
    )
    
    _llm_engine.add_openai_compatible_endpoint(endpoint)
    
    return EndpointResponse(
        name=endpoint.name,
        base_url=endpoint.base_url,
        model=endpoint.model,
        enabled=endpoint.enabled,
        timeout=endpoint.timeout,
    )


@router.delete("/endpoints/{name}")
async def remove_endpoint(name: str):
    """Remove an OpenAI-compatible endpoint by name."""
    if not _llm_engine:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    
    if _llm_engine.remove_openai_compatible_endpoint(name):
        return {"message": f"Endpoint '{name}' removed"}
    
    raise HTTPException(status_code=404, detail=f"Endpoint '{name}' not found")


@router.patch("/endpoints/{name}", response_model=EndpointResponse)
async def update_endpoint(name: str, data: EndpointCreate):
    """Update an existing OpenAI-compatible endpoint."""
    if not _llm_engine:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    
    # Remove and re-add with new settings
    if not _llm_engine.remove_openai_compatible_endpoint(name):
        raise HTTPException(status_code=404, detail=f"Endpoint '{name}' not found")
    
    endpoint = OpenAICompatibleEndpoint(
        name=data.name,
        api_key=data.api_key,
        base_url=data.base_url,
        model=data.model,
        enabled=data.enabled,
        timeout=data.timeout,
    )
    
    _llm_engine.add_openai_compatible_endpoint(endpoint)
    
    return EndpointResponse(
        name=endpoint.name,
        base_url=endpoint.base_url,
        model=endpoint.model,
        enabled=endpoint.enabled,
        timeout=endpoint.timeout,
    )


@router.post("/test")
async def test_connection(provider: Optional[str] = None, model: Optional[str] = None):
    """Test connection to an LLM provider.
    
    Args:
        provider: Provider name (e.g., 'openai', 'openai_compatible:my-endpoint')
        model: Model to test (optional, uses default if not provided)
    
    Returns:
        Connection test result
    """
    if not _llm_engine:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    
    try:
        from purple_team_gpt.core.llm.engine import Conversation
        
        conversation = Conversation()
        conversation.add_user("Reply with 'OK' to confirm connection.")
        
        response = await _llm_engine.quick_ask(
            prompt="Reply with 'OK' to confirm connection.",
            system="You are a connection test assistant. Reply briefly.",
        )
        
        return {
            "success": True,
            "provider": provider or _llm_engine.settings.default_provider,
            "model": model or _llm_engine.settings.default_model,
            "response_preview": response[:100],
        }
    except Exception as e:
        return {
            "success": False,
            "provider": provider,
            "model": model,
            "error": str(e),
        }