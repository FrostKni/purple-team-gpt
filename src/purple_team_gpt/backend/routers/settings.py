"""Settings endpoints.

This module provides REST endpoints for:
- Getting application settings
- Updating settings
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from purple_team_gpt.backend.security import (
    get_current_user,
    rate_limit_dependency,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class SettingsResponse(BaseModel):
    """Response model for settings."""

    llm_provider: str
    llm_model: str
    llm_failover: str
    vector_db: str
    vector_db_status: str
    message_queue: str
    message_queue_status: str
    management_network: str
    attack_network: str
    safe_mode: bool
    max_concurrent_tasks: int


@router.get("/", response_model=SettingsResponse)
async def get_settings(
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SettingsResponse:
    """Get application settings.

    Returns current configuration settings for the application.
    Requires authentication.
    """
    from purple_team_gpt.config import get_settings as get_app_settings

    settings = get_app_settings()

    return SettingsResponse(
        llm_provider=settings.llm.default_provider,
        llm_model=settings.llm.default_model,
        llm_failover="enabled" if settings.llm.enable_failover else "disabled",
        vector_db="ChromaDB",
        vector_db_status="healthy",
        message_queue="Redis",
        message_queue_status="healthy",
        management_network="purple-team-network",
        attack_network="attack-network",
        safe_mode=settings.agent.safe_mode,
        max_concurrent_tasks=5,
    )
