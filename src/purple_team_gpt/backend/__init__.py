"""Backend API with FastAPI routers.

This module provides the FastAPI backend for Purple Team GPT,
including REST endpoints and WebSocket support for real-time updates.
"""

from purple_team_gpt.backend.main import app

__all__ = ["app"]