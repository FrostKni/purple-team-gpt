"""Session management endpoints.

This module provides REST endpoints for:
- Creating simulation sessions
- Starting, pausing, resuming, and stopping sessions
- Getting session details and metrics
- Listing all sessions

All endpoints require JWT authentication.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from purple_team_gpt.core.orchestrator import SessionStatus, PurpleOrchestrator
from purple_team_gpt.backend.security import (
    get_current_user,
    rate_limit_dependency,
    validate_session_id,
    validate_target,
    sanitize_input,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Global orchestrator reference - set by main.py during lifespan
_orchestrator: Optional[PurpleOrchestrator] = None


def set_orchestrator(orch: PurpleOrchestrator) -> None:
    """Set the orchestrator reference.
    
    Called by main.py during application startup.
    """
    global _orchestrator
    _orchestrator = orch


def get_orchestrator() -> PurpleOrchestrator:
    """Get the orchestrator instance.
    
    Raises HTTPException if orchestrator is not initialized.
    """
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return _orchestrator


# Request/Response Models
class SessionCreate(BaseModel):
    """Request model for creating a new session."""
    target: str = Field(..., description="Target system/network for assessment")
    scope: str = Field("", description="Scope restrictions and constraints")
    metadata: Optional[dict] = Field(default=None, description="Additional session metadata")
    
    @field_validator("target")
    @classmethod
    def validate_target_field(cls, v: str) -> str:
        """Validate target field."""
        return validate_target(v)
    
    @field_validator("scope")
    @classmethod
    def validate_scope_field(cls, v: str) -> str:
        """Validate and sanitize scope field."""
        return sanitize_input(v, max_length=2000)


class SessionResponse(BaseModel):
    """Response model for session data."""
    id: str
    target: str
    scope: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SessionListResponse(BaseModel):
    """Response model for session list."""
    sessions: List[SessionResponse]
    total: int


class SessionMetricsResponse(BaseModel):
    """Response model for session metrics."""
    session_id: str
    target: str
    scope: str
    status: str
    duration: str
    red_agent: dict
    blue_agent: dict
    total_findings: int
    total_events: int


class SessionActionResponse(BaseModel):
    """Response model for session actions (start, stop, pause, resume)."""
    message: str
    session_id: str
    status: str


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SessionResponse:
    """Create a new simulation session.
    
    Creates a new session with Red and Blue agents initialized for
    the specified target. The session starts in PENDING status.
    
    Requires authentication.
    """
    orch = get_orchestrator()
    
    # Validate and sanitize inputs
    target = validate_target(data.target)
    scope = sanitize_input(data.scope, max_length=2000)
    
    session = orch.create_session(
        target=target,
        scope=scope,
        metadata=data.metadata,
    )
    
    logger.info(
        f"User {current_user.get('sub', 'unknown')} created session {session.id} "
        f"for target {target}"
    )
    
    return SessionResponse(
        id=session.id,
        target=session.target,
        scope=session.scope,
        status=session.status.value,
        created_at=session.created_at.isoformat() if session.created_at else None,
        started_at=session.started_at.isoformat() if session.started_at else None,
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
    )


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SessionListResponse:
    """List all sessions, optionally filtered by status.
    
    Returns a list of all sessions, with optional filtering by status.
    Requires authentication.
    """
    orch = get_orchestrator()
    
    status_filter = None
    if status:
        try:
            status_filter = SessionStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: {[s.value for s in SessionStatus]}",
            )
    
    sessions = orch.list_sessions(status=status_filter)
    
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                target=s.target,
                scope=s.scope,
                status=s.status.value,
                created_at=s.created_at.isoformat() if s.created_at else None,
                started_at=s.started_at.isoformat() if s.started_at else None,
                completed_at=s.completed_at.isoformat() if s.completed_at else None,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SessionResponse:
    """Get session details by ID.
    
    Returns detailed information about a specific session.
    Requires authentication.
    """
    orch = get_orchestrator()
    
    # Validate session ID format
    session_id = validate_session_id(session_id)
    
    session = orch.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        id=session.id,
        target=session.target,
        scope=session.scope,
        status=session.status.value,
        created_at=session.created_at.isoformat() if session.created_at else None,
        started_at=session.started_at.isoformat() if session.started_at else None,
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
    )


@router.post("/{session_id}/start", response_model=SessionActionResponse)
async def start_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SessionActionResponse:
    """Start a simulation session.
    
    Starts the Red and Blue agents for the session in the background.
    The session must be in PENDING or PAUSED status.
    Requires authentication.
    """
    orch = get_orchestrator()
    
    # Validate session ID format
    session_id = validate_session_id(session_id)
    
    session = orch.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status == SessionStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Session already running")
    
    if session.status == SessionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot restart a completed session")
    
    # Start session in background
    orch.start_session_background(session_id)
    
    logger.info(
        f"User {current_user.get('sub', 'unknown')} started session {session_id}"
    )
    
    return SessionActionResponse(
        message="Session started",
        session_id=session_id,
        status=SessionStatus.RUNNING.value,
    )


@router.post("/{session_id}/pause", response_model=SessionActionResponse)
async def pause_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SessionActionResponse:
    """Pause a running session.
    
    Pauses both Red and Blue agents. Can be resumed later.
    Requires authentication.
    """
    orch = get_orchestrator()
    
    # Validate session ID format
    session_id = validate_session_id(session_id)
    
    session = orch.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not orch.pause_session(session_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot pause session - not running or not found",
        )
    
    logger.info(
        f"User {current_user.get('sub', 'unknown')} paused session {session_id}"
    )
    
    return SessionActionResponse(
        message="Session paused",
        session_id=session_id,
        status=SessionStatus.PAUSED.value,
    )


@router.post("/{session_id}/resume", response_model=SessionActionResponse)
async def resume_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SessionActionResponse:
    """Resume a paused session.
    
    Resumes execution of both Red and Blue agents.
    Requires authentication.
    """
    orch = get_orchestrator()
    
    # Validate session ID format
    session_id = validate_session_id(session_id)
    
    session = orch.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not orch.resume_session(session_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot resume session - not paused or not found",
        )
    
    logger.info(
        f"User {current_user.get('sub', 'unknown')} resumed session {session_id}"
    )
    
    return SessionActionResponse(
        message="Session resumed",
        session_id=session_id,
        status=SessionStatus.RUNNING.value,
    )


@router.post("/{session_id}/stop", response_model=SessionActionResponse)
async def stop_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SessionActionResponse:
    """Stop a session.
    
    Stops the session and returns the final state. Cannot be resumed.
    Requires authentication.
    """
    orch = get_orchestrator()
    
    # Validate session ID format
    session_id = validate_session_id(session_id)
    
    session = orch.stop_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.info(
        f"User {current_user.get('sub', 'unknown')} stopped session {session_id}"
    )
    
    return SessionActionResponse(
        message="Session stopped",
        session_id=session_id,
        status=SessionStatus.COMPLETED.value,
    )


@router.get("/{session_id}/metrics", response_model=SessionMetricsResponse)
async def get_session_metrics(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> SessionMetricsResponse:
    """Get detailed metrics for a session.
    
    Returns comprehensive metrics including findings counts,
    step counts, duration, and agent summaries.
    Requires authentication.
    """
    orch = get_orchestrator()
    
    # Validate session ID format
    session_id = validate_session_id(session_id)
    
    metrics = orch.get_metrics(session_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionMetricsResponse(
        session_id=metrics["session_id"],
        target=metrics["target"],
        scope=metrics["scope"],
        status=metrics["status"],
        duration=metrics["duration"],
        red_agent=metrics["red_agent"],
        blue_agent=metrics["blue_agent"],
        total_findings=metrics["total_findings"],
        total_events=metrics["total_events"],
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _rate: dict = Depends(rate_limit_dependency),
) -> dict:
    """Delete a session.
    
    Stops the session if running and removes all associated data.
    Requires authentication.
    """
    orch = get_orchestrator()
    
    # Validate session ID format
    session_id = validate_session_id(session_id)
    
    if not orch.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.info(
        f"User {current_user.get('sub', 'unknown')} deleted session {session_id}"
    )
    
    return {"message": "Session deleted", "session_id": session_id}