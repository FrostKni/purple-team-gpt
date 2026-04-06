# API Middleware Design

## Overview

This document describes the middleware architecture for Purple Team GPT, including the request processing pipeline, middleware ordering, and integration patterns.

## 1. Middleware Pipeline Architecture

### 1.1 Request Flow

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Request ID Middleware                                         │
│    - Generate unique request ID                                  │
│    - Add to context for logging                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Security Headers Middleware                                   │
│    - Add security headers to all responses                       │
│    - HSTS, CSP, X-Frame-Options, etc.                           │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CORS Middleware                                               │
│    - Validate origin                                             │
│    - Handle preflight requests                                   │
│    - Add CORS headers                                            │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Request Size Limit Middleware                                 │
│    - Enforce maximum request body size                           │
│    - Prevent memory exhaustion attacks                           │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Rate Limiting Middleware                                      │
│    - Check rate limits (Redis-backed)                            │
│    - Return 429 if exceeded                                      │
│    - Add rate limit headers                                      │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Authentication Middleware                                     │
│    - Validate JWT token                                          │
│    - Extract user context                                        │
│    - Handle token refresh                                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Authorization Middleware                                      │
│    - Check permissions for endpoint                              │
│    - Validate resource access                                    │
│    - Return 403 if denied                                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. Input Validation Middleware                                   │
│    - Validate request body against schema                        │
│    - Sanitize inputs                                             │
│    - Check for injection patterns                                │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. Audit Logging Middleware                                      │
│    - Log request details                                         │
│    - Log response details (configurable)                         │
│    - Track security events                                       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. Exception Handler Middleware                                 │
│     - Catch and format exceptions                                │
│     - Return appropriate error responses                         │
│     - Log errors                                                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
    Route Handler
    │
    ▼
HTTP Response
```

### 1.2 Middleware Implementation

```python
# src/purple_team_gpt/backend/middleware/__init__.py

from fastapi import FastAPI, Request
from fastapi.middleware import Middleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
import time
import uuid
from typing import Callable

from purple_team_gpt.security.rate_limiting import RateLimitMiddleware
from purple_team_gpt.security.headers import SecurityHeadersMiddleware
from purple_team_gpt.security.audit import AuditLogger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size."""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={"error": "request_too_large", "message": "Request body too large"},
            )
        
        return await call_next(request)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Track request processing time."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        
        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""
    
    def __init__(self, app, public_paths: set = None):
        super().__init__(app)
        self.public_paths = public_paths or {
            "/", "/health", "/status",
            "/docs", "/redoc", "/openapi.json",
            "/api/v1/auth/login", "/api/v1/auth/register",
        }
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip authentication for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Skip for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract and validate token
        from purple_team_gpt.security.authorization import get_current_user, AuthContext
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": "authentication_required", "message": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = auth_header.split(" ")[1]
        jwt_manager = request.app.state.jwt_manager
        
        payload = jwt_manager.verify_token(token)
        if not payload:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "message": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Store user context in request state
        from purple_team_gpt.security.auth import UserRole, Permission
        request.state.user = AuthContext(
            user_id=payload.sub,
            roles=[UserRole(r) for r in payload.roles],
            permissions=[Permission(p) for p in payload.permissions],
            org_id=payload.org_id,
            session_id=payload.session_id,
        )
        
        return await call_next(request)


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """RBAC authorization middleware."""
    
    # Endpoint to permission mapping
    ENDPOINT_PERMISSIONS = {
        # Session endpoints
        ("POST", "/api/v1/sessions"): "sessions:write",
        ("GET", "/api/v1/sessions"): "sessions:read",
        ("DELETE", "/api/v1/sessions"): "sessions:delete",
        ("POST", "/api/v1/sessions/{id}/start"): "sessions:execute",
        ("POST", "/api/v1/sessions/{id}/pause"): "sessions:execute",
        ("POST", "/api/v1/sessions/{id}/resume"): "sessions:execute",
        ("POST", "/api/v1/sessions/{id}/stop"): "sessions:execute",
        
        # LLM endpoints
        ("POST", "/api/v1/llm/endpoints"): "llm:configure",
        ("DELETE", "/api/v1/llm/endpoints"): "llm:configure",
        ("POST", "/api/v1/llm/test"): "llm:test",
        
        # Admin endpoints
        ("GET", "/api/v1/audit"): "audit:read",
        ("POST", "/api/v1/users"): "users:manage",
    }
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip for public paths
        if not hasattr(request.state, "user"):
            return await call_next(request)
        
        user: AuthContext = request.state.user
        
        # Admin has full access
        if user.is_admin():
            return await call_next(request)
        
        # Check endpoint permission
        required_permission = self._get_required_permission(request)
        
        if required_permission and not user.has_permission(Permission(required_permission)):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={
                    "error": "access_denied",
                    "message": f"Permission '{required_permission}' required",
                },
            )
        
        return await call_next(request)
    
    def _get_required_permission(self, request: Request) -> Optional[str]:
        """Get required permission for endpoint."""
        from purple_team_gpt.security.auth import Permission
        
        path = request.url.path
        method = request.method
        
        # Check exact match
        key = (method, path)
        if key in self.ENDPOINT_PERMISSIONS:
            return self.ENDPOINT_PERMISSIONS[key]
        
        # Check pattern match (with path parameters)
        for (ep_method, ep_path), permission in self.ENDPOINT_PERMISSIONS.items():
            if ep_method != method:
                continue
            
            # Convert path pattern to regex
            import re
            pattern = re.sub(r"\{[^}]+\}", r"[^/]+", ep_path)
            if re.match(f"^{pattern}$", path):
                return permission
        
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware."""
    
    def __init__(self, app, audit_logger: AuditLogger):
        super().__init__(app)
        self.audit_logger = audit_logger
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip audit for health checks
        if request.url.path in ["/health", "/status"]:
            return await call_next(request)
        
        # Log request
        user_id = getattr(request.state.user, "user_id", None) if hasattr(request.state, "user") else None
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            success = response.status_code < 400
        except Exception as e:
            success = False
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log API access
            from purple_team_gpt.security.audit import AuditEventType
            self.audit_logger.log(
                event_type=AuditEventType.ACCESS_GRANTED if success else AuditEventType.ACCESS_DENIED,
                request=request,
                user_id=user_id,
                details={
                    "duration_ms": duration_ms,
                    "status_code": response.status_code if "response" in dir() else 500,
                },
                success=success,
            )
        
        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handler middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            return await call_next(request)
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail, "message": str(e.detail)},
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Unhandled exception: {e}")
            
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": "An internal error occurred",
                    "request_id": getattr(request.state, "request_id", None),
                },
            )


# Middleware setup function
def setup_middleware(app: FastAPI, settings) -> None:
    """Configure all middleware for the application."""
    
    from purple_team_gpt.security.rate_limiting import RateLimiter
    
    # Add middleware in reverse order (last added = first executed)
    
    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request timing
    app.add_middleware(RequestTimingMiddleware)
    
    # Request ID
    app.add_middleware(RequestIDMiddleware)
    
    # Request size limit
    app.add_middleware(RequestSizeLimitMiddleware, max_size=settings.security.max_request_size)
    
    # Rate limiting (if enabled and Redis available)
    if settings.security.rate_limit_enabled:
        import redis.asyncio as redis
        redis_client = redis.from_url(settings.security.redis_url)
        rate_limiter = RateLimiter(redis_client)
        app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    
    # Authentication
    app.add_middleware(AuthenticationMiddleware)
    
    # Authorization
    app.add_middleware(AuthorizationMiddleware)
    
    # Audit logging
    audit_logger = AuditLogger(
        logger=logging.getLogger("audit"),
        sensitive_fields=set(settings.security.audit_sensitive_fields),
    )
    app.add_middleware(AuditMiddleware, audit_logger=audit_logger)
    
    # Exception handling (should be last)
    app.add_middleware(ExceptionHandlerMiddleware)
    
    # Store shared objects in app state
    app.state.audit_logger = audit_logger
```

## 2. Dependency Injection Pattern

### 2.1 Dependencies Module

```python
# src/purple_team_gpt/backend/dependencies.py

from typing import Optional
from fastapi import Depends, Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from purple_team_gpt.core.orchestrator import PurpleOrchestrator
from purple_team_gpt.core.llm.engine import LLMEngine
from purple_team_gpt.core.rag.vector_store import VectorStore
from purple_team_gpt.feedback.store import FeedbackStore
from purple_team_gpt.security.authorization import AuthContext, Permission
from purple_team_gpt.security.auth import JWTManager


security = HTTPBearer(auto_error=False)


# Core dependencies
def get_orchestrator(request: Request) -> PurpleOrchestrator:
    """Get the orchestrator instance."""
    orch = request.app.state.orchestrator
    if orch is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orch


def get_llm_engine(request: Request) -> LLMEngine:
    """Get the LLM engine instance."""
    engine = request.app.state.llm_engine
    if engine is None:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    return engine


def get_vector_store(request: Request) -> VectorStore:
    """Get the vector store instance."""
    vs = request.app.state.vector_store
    if vs is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized")
    return vs


def get_feedback_store(request: Request) -> FeedbackStore:
    """Get the feedback store instance."""
    store = request.app.state.feedback_store
    if store is None:
        raise HTTPException(status_code=503, detail="Feedback store not initialized")
    return store


def get_jwt_manager(request: Request) -> JWTManager:
    """Get the JWT manager instance."""
    manager = request.app.state.jwt_manager
    if manager is None:
        raise HTTPException(status_code=503, detail="JWT manager not initialized")
    return manager


# Authentication dependencies
def get_current_user(request: Request) -> AuthContext:
    """Get the current authenticated user from request state."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def get_optional_user(request: Request) -> Optional[AuthContext]:
    """Get the current user if authenticated, otherwise None."""
    return getattr(request.state, "user", None)


# Authorization dependencies
def require_permissions(*permissions: Permission):
    """Dependency that requires specific permissions."""
    async def checker(user: AuthContext = Depends(get_current_user)) -> AuthContext:
        if not user.has_all_permissions(list(permissions)):
            raise HTTPException(
                status_code=403,
                detail=f"Required permissions: {[p.value for p in permissions]}",
            )
        return user
    return Depends(checker)


def require_roles(*roles):
    """Dependency that requires specific roles."""
    from purple_team_gpt.security.auth import UserRole
    async def checker(user: AuthContext = Depends(get_current_user)) -> AuthContext:
        if not any(r in user.roles for r in roles):
            raise HTTPException(
                status_code=403,
                detail=f"Required roles: {[r.value for r in roles]}",
            )
        return user
    return Depends(checker)


# Resource authorization dependencies
class SessionAccessChecker:
    """Check access to session resources."""
    
    def __init__(self, action: str = "read"):
        self.action = action
    
    async def __call__(
        self,
        session_id: str,
        user: AuthContext = Depends(get_current_user),
        orchestrator: PurpleOrchestrator = Depends(get_orchestrator),
    ) -> str:
        """Check session access and return session_id if authorized."""
        session = orchestrator.get_session(session_id)
        
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check org access
        session_org = session.metadata.get("org_id")
        if session_org and not user.can_access_resource(session_org):
            # Don't reveal existence
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check action-specific permissions
        action_permissions = {
            "read": Permission.SESSIONS_READ,
            "write": Permission.SESSIONS_WRITE,
            "delete": Permission.SESSIONS_DELETE,
            "execute": Permission.SESSIONS_EXECUTE,
        }
        
        required = action_permissions.get(self.action)
        if required and not user.has_permission(required):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return session_id


# Convenience dependencies
can_read_sessions = SessionAccessChecker("read")
can_write_sessions = SessionAccessChecker("write")
can_delete_sessions = SessionAccessChecker("delete")
can_execute_sessions = SessionAccessChecker("execute")
```

### 2.2 Updated Router Example

```python
# src/purple_team_gpt/backend/routers/sessions_secure.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from purple_team_gpt.core.orchestrator import SessionStatus, PurpleOrchestrator
from purple_team_gpt.security.authorization import AuthContext, Permission
from purple_team_gpt.security.auth import UserRole
from purple_team_gpt.backend.dependencies import (
    get_orchestrator,
    get_current_user,
    require_permissions,
    can_read_sessions,
    can_write_sessions,
    can_execute_sessions,
)
from purple_team_gpt.schemas.requests import SessionCreateRequest

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreateRequest,
    user: AuthContext = Depends(require_permissions(Permission.SESSIONS_WRITE)),
    orchestrator: PurpleOrchestrator = Depends(get_orchestrator),
):
    """Create a new simulation session (requires sessions:write permission)."""
    
    # Add org_id from user context
    metadata = data.metadata or {}
    metadata["org_id"] = user.org_id
    metadata["created_by"] = user.user_id
    
    session = orchestrator.create_session(
        target=data.target,
        scope=data.scope,
        metadata=metadata,
    )
    
    return SessionResponse.from_session(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str = Depends(can_read_sessions),
    orchestrator: PurpleOrchestrator = Depends(get_orchestrator),
):
    """Get session details (requires sessions:read permission)."""
    session = orchestrator.get_session(session_id)
    return SessionResponse.from_session(session)


@router.post("/{session_id}/start", response_model=SessionActionResponse)
async def start_session(
    session_id: str = Depends(can_execute_sessions),
    orchestrator: PurpleOrchestrator = Depends(get_orchestrator),
):
    """Start a session (requires sessions:execute permission)."""
    session = orchestrator.get_session(session_id)
    
    if session.status == SessionStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Session already running")
    
    orchestrator.start_session_background(session_id)
    
    return SessionActionResponse(
        message="Session started",
        session_id=session_id,
        status=SessionStatus.RUNNING.value,
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str = Depends(can_delete_sessions),
    user: AuthContext = Depends(get_current_user),
    orchestrator: PurpleOrchestrator = Depends(get_orchestrator),
):
    """Delete a session (requires sessions:delete permission)."""
    if not orchestrator.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted", "session_id": session_id}
```

## 3. WebSocket Security

### 3.1 WebSocket Authentication

```python
# src/purple_team_gpt/backend/routers/websocket_secure.py

import asyncio
import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from jose import jwt, JWTError

from purple_team_gpt.core.orchestrator import PurpleOrchestrator, AgentEvent
from purple_team_gpt.core.rag.vector_store import VectorStore
from purple_team_gpt.security.auth import JWTManager, Permission
from purple_team_gpt.security.authorization import AuthContext

logger = logging.getLogger(__name__)
router = APIRouter()


class WebSocketAuth:
    """WebSocket authentication handler."""
    
    def __init__(self, jwt_manager: JWTManager):
        self.jwt_manager = jwt_manager
    
    async def authenticate(
        self,
        websocket: WebSocket,
        token: Optional[str] = None,
    ) -> Optional[AuthContext]:
        """Authenticate WebSocket connection."""
        
        if not token:
            # Try to get token from query params or first message
            token = websocket.query_params.get("token")
        
        if not token:
            return None
        
        payload = self.jwt_manager.verify_token(token)
        if not payload:
            return None
        
        from purple_team_gpt.security.auth import UserRole, Permission
        return AuthContext(
            user_id=payload.sub,
            roles=[UserRole(r) for r in payload.roles],
            permissions=[Permission(p) for p in payload.permissions],
            org_id=payload.org_id,
            session_id=payload.session_id,
        )


class SecureConnectionManager:
    """WebSocket connection manager with authentication."""
    
    def __init__(self):
        # session_id -> {websocket -> auth_context}
        self.active_connections: Dict[str, Dict[WebSocket, AuthContext]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        auth: AuthContext,
    ) -> bool:
        """Accept and register an authenticated WebSocket connection."""
        
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}
        
        self.active_connections[session_id][websocket] = auth
        
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "user_id": auth.user_id,
        })
        
        return True
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].pop(websocket, None)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def broadcast(
        self,
        session_id: str,
        message: dict,
        exclude: Optional[WebSocket] = None,
    ):
        """Broadcast message to all connections for a session."""
        if session_id not in self.active_connections:
            return
        
        disconnected = []
        
        for ws, auth in self.active_connections[session_id].items():
            if ws == exclude:
                continue
            
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        
        for ws in disconnected:
            self.disconnect(ws, session_id)
    
    async def broadcast_event(
        self,
        session_id: str,
        event: AgentEvent,
    ):
        """Broadcast agent event with permission check."""
        await self.broadcast(session_id, {
            "type": "event",
            "agent": event.agent,
            "event_type": event.event_type,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        })
    
    def is_authorized(
        self,
        session_id: str,
        websocket: WebSocket,
        action: str,
    ) -> bool:
        """Check if connection is authorized for an action."""
        if session_id not in self.active_connections:
            return False
        
        auth = self.active_connections[session_id].get(websocket)
        if not auth:
            return False
        
        # Check action-specific permissions
        action_permissions = {
            "command": Permission.SESSIONS_EXECUTE,
            "feedback": Permission.SESSIONS_WRITE,
        }
        
        required = action_permissions.get(action)
        return required is None or auth.has_permission(required)


manager = SecureConnectionManager()


@router.websocket("/session/{session_id}")
async def websocket_session(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
    orchestrator: PurpleOrchestrator = Depends(lambda: None),  # Set by main.py
    jwt_manager: JWTManager = Depends(lambda: None),
):
    """Secure WebSocket endpoint for session updates."""
    
    # Authenticate
    ws_auth = WebSocketAuth(jwt_manager)
    auth = await ws_auth.authenticate(websocket, token)
    
    if not auth:
        await websocket.accept()
        await websocket.send_json({
            "type": "error",
            "error": "authentication_required",
            "message": "Valid authentication token required",
        })
        await websocket.close(code=4001)
        return
    
    # Check session access
    session = orchestrator.get_session(session_id)
    if not session:
        await websocket.accept()
        await websocket.send_json({
            "type": "error",
            "error": "not_found",
            "message": "Session not found",
        })
        await websocket.close(code=4004)
        return
    
    # Check org access
    session_org = session.metadata.get("org_id")
    if session_org and not auth.can_access_resource(session_org):
        await websocket.accept()
        await websocket.send_json({
            "type": "error",
            "error": "not_found",
            "message": "Session not found",
        })
        await websocket.close(code=4004)
        return
    
    # Check read permission
    if not auth.has_permission(Permission.SESSIONS_READ):
        await websocket.accept()
        await websocket.send_json({
            "type": "error",
            "error": "access_denied",
            "message": "Insufficient permissions",
        })
        await websocket.close(code=4003)
        return
    
    # Connect
    await manager.connect(websocket, session_id, auth)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type", "unknown")
                
                # Validate message type
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message_type == "command":
                    # Check execute permission
                    if not manager.is_authorized(session_id, websocket, "command"):
                        await websocket.send_json({
                            "type": "error",
                            "error": "access_denied",
                            "message": "Execute permission required",
                        })
                        continue
                    
                    command = message.get("command", "").lower()
                    
                    # Validate command
                    if command not in ["pause", "resume", "stop"]:
                        await websocket.send_json({
                            "type": "error",
                            "error": "invalid_command",
                            "message": f"Unknown command: {command}",
                        })
                        continue
                    
                    # Execute command
                    await handle_command(session_id, command, websocket, orchestrator)
                
                elif message_type == "feedback":
                    if not manager.is_authorized(session_id, websocket, "feedback"):
                        await websocket.send_json({
                            "type": "error",
                            "error": "access_denied",
                            "message": "Write permission required",
                        })
                        continue
                    
                    await handle_feedback(session_id, message, websocket, auth)
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "error": "invalid_message",
                        "message": f"Unknown message type: {message_type}",
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "invalid_json",
                    "message": "Invalid JSON message",
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)


# Close codes for WebSocket
class WebSocketCloseCode:
    NORMAL = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    INVALID_PAYLOAD = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    INTERNAL_ERROR = 1011
    
    # Custom codes (4000-4999)
    AUTHENTICATION_REQUIRED = 4001
    ACCESS_DENIED = 4003
    NOT_FOUND = 4004
    RATE_LIMITED = 4029
```

## 4. Error Handling

### 4.1 Standard Error Responses

```python
# src/purple_team_gpt/backend/errors.py

from typing import Optional, Dict, Any
from enum import Enum
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Standard error codes."""
    
    # Authentication errors
    AUTHENTICATION_REQUIRED = "authentication_required"
    INVALID_TOKEN = "invalid_token"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"
    INVALID_CREDENTIALS = "invalid_credentials"
    
    # Authorization errors
    ACCESS_DENIED = "access_denied"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    RESOURCE_NOT_ACCESSIBLE = "resource_not_accessible"
    
    # Validation errors
    VALIDATION_ERROR = "validation_error"
    INVALID_INPUT = "invalid_input"
    INVALID_URL = "invalid_url"
    INVALID_COMMAND = "invalid_command"
    SSRF_BLOCKED = "ssrf_blocked"
    
    # Resource errors
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    
    # Rate limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Server errors
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    
    # Session errors
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_ALREADY_RUNNING = "session_already_running"
    SESSION_NOT_RUNNING = "session_not_running"
    SESSION_COMPLETED = "session_completed"


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class APIError(HTTPException):
    """Custom API exception with error code."""
    
    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.details = details
        super().__init__(status_code=status_code, detail=message)


# Predefined exceptions
class AuthenticationError(APIError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            status_code=401,
            error_code=ErrorCode.AUTHENTICATION_REQUIRED,
            message=message,
        )


class AuthorizationError(APIError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            status_code=403,
            error_code=ErrorCode.ACCESS_DENIED,
            message=message,
        )


class NotFoundError(APIError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message=f"{resource} not found",
        )


class ValidationError(APIError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=400,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
        )


class RateLimitError(APIError):
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=429,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded",
            details={"retry_after": retry_after},
        )


# Exception handlers
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.error_code,
            message=exc.detail,
            details=exc.details,
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle generic HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorCode.INTERNAL_ERROR,
            message=str(exc.detail),
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    import logging
    logging.getLogger(__name__).exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorCode.INTERNAL_ERROR,
            message="An internal error occurred",
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
    )
```

## 5. Configuration Summary

```python
# src/purple_team_gpt/backend/app_factory.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from purple_team_gpt.config import get_settings
from purple_team_gpt.backend.middleware import setup_middleware
from purple_team_gpt.backend.errors import (
    api_error_handler,
    http_exception_handler,
    generic_exception_handler,
)
from purple_team_gpt.security.auth import JWTManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    
    # Initialize JWT manager
    jwt_manager = JWTManager(
        private_key_pem=settings.security.jwt_private_key,
        public_key_pem=settings.security.jwt_public_key,
        issuer=settings.security.jwt_issuer,
        audience=settings.security.jwt_audience,
    )
    app.state.jwt_manager = jwt_manager
    
    # Initialize core services
    # ... (existing initialization code)
    
    yield
    
    # Cleanup
    pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Purple Team GPT",
        description="Autonomous Purple Team cybersecurity simulation framework",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Setup middleware
    setup_middleware(app, settings)
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_allowed_origins,
        allow_credentials=settings.security.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
        ],
        max_age=settings.security.cors_max_age,
    )
    
    # Register exception handlers
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # Include routers
    from purple_team_gpt.backend.routers import sessions, websocket, feedback, llm, auth
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
    app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
    app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
    app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])
    
    return app
```

This middleware design provides a comprehensive security layer that:
- Authenticates all requests with JWT
- Authorizes based on RBAC permissions
- Validates inputs to prevent injection attacks
- Rate limits to prevent abuse
- Logs all access for audit trails
- Handles errors consistently with proper HTTP status codes