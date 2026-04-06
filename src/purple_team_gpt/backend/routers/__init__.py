"""FastAPI routers for API endpoints.

This package contains routers for:
- auth: Authentication endpoints (register, login, me)
- users: User management endpoints (list, get by ID)
- sessions: Session management endpoints
- websocket: Real-time WebSocket communication
- feedback: Human feedback management endpoints
- llm: LLM provider management endpoints
"""

from purple_team_gpt.backend.routers import auth, feedback, llm, sessions, users, websocket

__all__ = ["auth", "users", "sessions", "websocket", "feedback", "llm"]
