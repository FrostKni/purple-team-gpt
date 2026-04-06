# Purple Team GPT - Architectural Improvements

## Executive Summary

This document summarizes the architectural issues identified in the current Purple Team GPT codebase and proposes improvements for production readiness.

---

## 1. Current Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React/Vue)                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ Sessions    │  │ WebSocket   │  │ LLM Config  │  │ Feedback    │   │
│  │ Router      │  │ Router      │  │ Router      │  │ Router      │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Global State (Module-level)                   │   │
│  │  - orchestrator: Optional[PurpleOrchestrator]                    │   │
│  │  - llm_engine: Optional[LLMEngine]                               │   │
│  │  - vector_store: Optional[VectorStore]                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   LLM Providers     │  │   ChromaDB          │  │   SQLite            │
│   (OpenAI, etc.)    │  │   (Vector Store)    │  │   (Feedback)        │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## 2. Identified Architectural Issues

### 2.1 Security Issues

| Issue | Location | Severity | Impact |
|-------|----------|----------|--------|
| No Authentication | All routers | CRITICAL | Anyone can access all endpoints |
| No Authorization | All routers | CRITICAL | No access control |
| SSRF Vulnerability | `llm.py:79-118` | HIGH | Arbitrary URL via endpoint config |
| Command Injection Risk | `tool_manager.py` | HIGH | Unsafe tool execution |
| CORS Too Permissive | `main.py:118` | MEDIUM | `allow_headers=["*"]` |
| WebSocket No Auth | `websocket.py:179` | HIGH | Unauthenticated WS connections |
| API Keys in Memory | `llm/engine.py` | MEDIUM | Keys in clear text |

### 2.2 Design Issues

| Issue | Location | Description |
|-------|----------|-------------|
| Global State | `main.py:29-33` | Module-level variables instead of DI |
| No Dependency Injection | All routers | Direct module imports |
| Session Storage in Memory | `orchestrator.py:156` | Sessions lost on restart |
| No Persistence | Sessions | No database backing for sessions |
| Error Handling | Various | Inconsistent error responses |
| No Audit Trail | All | No security event logging |

---

## 3. Proposed Improvements

### 3.1 Agent Orchestration Improvements

**Current State:**
```python
# orchestrator.py
class PurpleOrchestrator:
    def __init__(self, ...):
        self.sessions: Dict[str, Session] = {}  # In-memory only
        self.red_agents: Dict[str, RedAgent] = {}
        self.blue_agents: Dict[str, BlueAgent] = {}
```

**Issues:**
1. Sessions stored only in memory - lost on restart
2. No persistence layer
3. No session history
4. No concurrent session limits

**Proposed Solution:**

```python
# Proposed architecture
class SessionRepository:
    """Abstract session persistence."""
    
    async def save(self, session: Session) -> Session: ...
    async def get(self, session_id: str) -> Optional[Session]: ...
    async def list(self, filters: SessionFilters) -> List[Session]: ...
    async def delete(self, session_id: str) -> bool: ...


class SqlSessionRepository(SessionRepository):
    """SQL-backed session storage."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def save(self, session: Session) -> Session:
        # Convert to DB model and persist
        db_session = SessionModel.from_domain(session)
        self.db.add(db_session)
        await self.db.commit()
        return session


class RedisSessionCache:
    """Redis cache for active sessions."""
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def get_active(self, session_id: str) -> Optional[Session]:
        data = await self.redis.get(f"session:active:{session_id}")
        if data:
            return Session.from_json(data)
        return None
    
    async def set_active(self, session: Session, ttl: int = 3600):
        await self.redis.setex(
            f"session:active:{session_id}",
            ttl,
            session.to_json(),
        )


class PurpleOrchestratorV2:
    """Improved orchestrator with persistence."""
    
    def __init__(
        self,
        session_repo: SessionRepository,
        session_cache: RedisSessionCache,
        llm_engine: LLMEngine,
        event_bus: EventBus,
    ):
        self.session_repo = session_repo
        self.session_cache = session_cache
        self.llm_engine = llm_engine
        self.event_bus = event_bus
        
        # Active agent tasks (not session state)
        self._agent_tasks: Dict[str, asyncio.Task] = {}
    
    async def create_session(
        self,
        target: str,
        scope: str,
        user_id: str,
        org_id: str,
    ) -> Session:
        """Create and persist a new session."""
        session = Session(
            target=target,
            scope=scope,
            created_by=user_id,
            org_id=org_id,
        )
        
        # Persist
        session = await self.session_repo.save(session)
        
        # Cache for fast access
        await self.session_cache.set_active(session)
        
        # Publish event
        await self.event_bus.publish(SessionCreatedEvent(session))
        
        return session
```

### 3.2 WebSocket Handling Improvements

**Current State:**
```python
# websocket.py - No authentication, no message validation
@router.websocket("/session/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    # No auth check, no rate limiting
```

**Proposed Solution:**

```python
# Improved WebSocket handling
class WebSocketMessage(BaseModel):
    """Validated WebSocket message."""
    type: str
    data: Dict[str, Any] = {}
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"ping", "command", "feedback", "get_metrics", "subscribe"}
        if v not in allowed:
            raise ValueError(f"Invalid message type: {v}")
        return v


class WebSocketRateLimiter:
    """Per-connection rate limiting."""
    
    def __init__(self, max_messages: int = 100, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._counts: Dict[str, List[float]] = {}
    
    def is_allowed(self, connection_id: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        
        if connection_id not in self._counts:
            self._counts[connection_id] = []
        
        # Clean old entries
        self._counts[connection_id] = [
            t for t in self._counts[connection_id] if t > cutoff
        ]
        
        if len(self._counts[connection_id]) >= self.max_messages:
            return False
        
        self._counts[connection_id].append(now)
        return True


@router.websocket("/session/{session_id}")
async def websocket_session(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    auth: AuthContext = Depends(websocket_auth),
    rate_limiter: WebSocketRateLimiter = Depends(get_rate_limiter),
):
    """Secure WebSocket endpoint."""
    
    # Validate token before accepting connection
    if not auth:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    # Check session access
    if not await can_access_session(auth, session_id):
        await websocket.close(code=4003, reason="Access denied")
        return
    
    # Accept connection
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, session_id, auth, connection_id)
    
    try:
        while True:
            # Rate limit check
            if not rate_limiter.is_allowed(connection_id):
                await websocket.send_json({
                    "type": "error",
                    "error": "rate_limit",
                    "message": "Too many messages",
                })
                continue
            
            # Receive and validate message
            raw_data = await websocket.receive_text()
            
            try:
                message = WebSocketMessage.model_validate_json(raw_data)
            except ValidationError as e:
                await websocket.send_json({
                    "type": "error",
                    "error": "validation",
                    "message": str(e),
                })
                continue
            
            # Handle message
            await handle_websocket_message(message, websocket, session_id, auth)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    finally:
        rate_limiter.cleanup(connection_id)
```

### 3.3 Vector Store Integration Improvements

**Current State:**
- ChromaDB with local persistence
- No access control
- No encryption
- Single instance (no scaling)

**Proposed Solution:**

```python
class VectorStoreService:
    """Enhanced vector store with access control."""
    
    def __init__(
        self,
        chroma_client: chromadb.ClientAPI,
        embedding_engine: EmbeddingEngine,
        access_control: AccessControlService,
    ):
        self.client = chroma_client
        self.embeddings = embedding_engine
        self.access_control = access_control
    
    async def query(
        self,
        collection_name: str,
        query_text: str,
        auth: AuthContext,
        n_results: int = 5,
    ) -> Dict[str, Any]:
        """Query with access control."""
        
        # Check collection access
        if not await self.access_control.can_read_collection(auth, collection_name):
            raise AccessDeniedError(f"Cannot access collection: {collection_name}")
        
        # Build metadata filter for org isolation
        where_filter = {}
        if not auth.is_admin():
            where_filter["org_id"] = auth.org_id
        
        # Query
        collection = self.client.get_collection(collection_name)
        results = collection.query(
            query_embeddings=await self.embeddings.embed([query_text]),
            n_results=n_results,
            where=where_filter,
        )
        
        # Audit log
        await self.access_control.audit_vector_query(
            auth, collection_name, query_text,
        )
        
        return results
    
    async def add(
        self,
        collection_name: str,
        documents: List[str],
        auth: AuthContext,
        metadatas: Optional[List[Dict]] = None,
    ) -> List[str]:
        """Add documents with org isolation."""
        
        # Check write access
        if not await self.access_control.can_write_collection(auth, collection_name):
            raise AccessDeniedError(f"Cannot write to collection: {collection_name}")
        
        # Add org_id to metadata
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        for meta in metadatas:
            meta["org_id"] = auth.org_id
            meta["created_by"] = auth.user_id
            meta["created_at"] = datetime.utcnow().isoformat()
        
        # Add documents
        collection = self.client.get_or_create_collection(collection_name)
        ids = [str(uuid.uuid4()) for _ in documents]
        
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=await self.embeddings.embed(documents),
            metadatas=metadatas,
        )
        
        return ids


class AccessControlService:
    """Service for access control decisions."""
    
    async def can_read_collection(
        self,
        auth: AuthContext,
        collection_name: str,
    ) -> bool:
        """Check read access to collection."""
        # Public collections
        if collection_name in ["attack_patterns", "defense_patterns"]:
            return auth.has_permission(Permission.FINDINGS_READ)
        
        # Org-specific collections
        if collection_name in ["session_logs", "feedback_store"]:
            return auth.has_permission(Permission.SESSIONS_READ)
        
        return False
    
    async def can_write_collection(
        self,
        auth: AuthContext,
        collection_name: str,
    ) -> bool:
        """Check write access to collection."""
        return auth.has_permission(Permission.SESSIONS_WRITE)
```

### 3.4 Error Handling Improvements

**Current State:**
- Inconsistent error responses
- No standardized error codes
- Stack traces in production

**Proposed Solution:**

```python
# Standard error handling
from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationError(AppException):
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            code="validation_error",
            message=message,
            status_code=400,
            details=details,
        )


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="not_found",
            message=f"{resource} not found: {identifier}",
            status_code=404,
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            code="authentication_required",
            message=message,
            status_code=401,
        )


class AuthorizationError(AppException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            code="access_denied",
            message=message,
            status_code=403,
        )


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """Global exception handler for AppException."""
    
    response = {
        "error": {
            "code": exc.code,
            "message": exc.message,
        },
        "request_id": getattr(request.state, "request_id", None),
    }
    
    if exc.details:
        response["error"]["details"] = exc.details
    
    # Only include stack trace in debug mode
    if settings.app.debug:
        response["error"]["traceback"] = traceback.format_exc()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
    )


# Usage in routers
@router.post("/sessions")
async def create_session(
    data: SessionCreate,
    auth: AuthContext = Depends(require_permission("sessions:write")),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    try:
        session = await orchestrator.create_session(
            target=data.target,
            scope=data.scope,
            user_id=auth.user_id,
            org_id=auth.org_id,
        )
    except TargetValidationError as e:
        raise ValidationError(
            message="Invalid target",
            details={"target": str(e)},
        )
    
    return SessionResponse.from_session(session)
```

### 3.5 Dependency Injection Pattern

**Current State:**
```python
# Global module-level state
llm_engine: Optional[LLMEngine] = None
vector_store: Optional[VectorStore] = None
orchestrator: Optional[PurpleOrchestrator] = None

def set_orchestrator(orch: PurpleOrchestrator) -> None:
    global orchestrator
    orchestrator = orch
```

**Proposed Solution:**

```python
# Proper dependency injection
from typing import Annotated
from fastapi import Depends


class AppContainer:
    """Application container for dependency injection."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm_engine: Optional[LLMEngine] = None
        self._vector_store: Optional[VectorStore] = None
        self._orchestrator: Optional[PurpleOrchestrator] = None
        self._session_repo: Optional[SessionRepository] = None
    
    @property
    def llm_engine(self) -> LLMEngine:
        if self._llm_engine is None:
            self._llm_engine = self._create_llm_engine()
        return self._llm_engine
    
    @property
    def vector_store(self) -> VectorStore:
        if self._vector_store is None:
            self._vector_store = self._create_vector_store()
        return self._vector_store
    
    @property
    def orchestrator(self) -> PurpleOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = PurpleOrchestrator(
                session_repo=self.session_repo,
                llm_engine=self.llm_engine,
                vector_store=self.vector_store,
            )
        return self._orchestrator
    
    @property
    def session_repo(self) -> SessionRepository:
        if self._session_repo is None:
            self._session_repo = SqlSessionRepository(self.db)
        return self._session_repo


# FastAPI dependencies
def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_llm_engine(
    container: Annotated[AppContainer, Depends(get_container)],
) -> LLMEngine:
    return container.llm_engine


def get_vector_store(
    container: Annotated[AppContainer, Depends(get_container)],
) -> VectorStore:
    return container.vector_store


def get_orchestrator(
    container: Annotated[AppContainer, Depends(get_container)],
) -> PurpleOrchestrator:
    return container.orchestrator


# Type aliases for cleaner injection
LLMEngineDep = Annotated[LLMEngine, Depends(get_llm_engine)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
OrchestratorDep = Annotated[PurpleOrchestrator, Depends(get_orchestrator)]


# Usage in routers
@router.post("/sessions")
async def create_session(
    data: SessionCreate,
    auth: AuthContextDep,
    orchestrator: OrchestratorDep,
):
    session = await orchestrator.create_session(...)
    return SessionResponse.from_session(session)
```

---

## 4. Implementation Priority

### Phase 1: Security Foundation (Week 1-2)
1. Implement JWT authentication
2. Add authorization middleware
3. Add rate limiting
4. Fix SSRF vulnerability in LLM config
5. Add WebSocket authentication

### Phase 2: Data Persistence (Week 2-3)
1. Implement session persistence
2. Create database schema
3. Add user management
4. Implement audit logging

### Phase 3: Architecture Improvements (Week 3-4)
1. Refactor to dependency injection
2. Improve error handling
3. Add vector store access control
4. Improve WebSocket handling

### Phase 4: Hardening (Week 4-5)
1. Security testing
2. Performance optimization
3. Documentation
4. Monitoring and alerting

---

## 5. Architecture Target State

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React/Vue)                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Load Balancer (Nginx/ALB)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Middleware Pipeline                           │   │
│  │  Security → Rate Limit → Auth → Authz → Validation → Audit       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Dependency Container                          │   │
│  │  - LLM Engine  - Vector Store  - Orchestrator  - Repositories    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Sessions │ │ WebSocket│ │   LLM    │ │ Feedback │ │   Auth   │    │
│  │ Router   │ │ Router   │ │ Router   │ │ Router   │ │ Router   │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │    Redis     │   │   ChromaDB   │   │ LLM Providers│
│  (Sessions,  │   │  (Cache,     │   │ (Vector      │   │ (OpenAI,     │
│   Users,     │   │   Rate Limit)│   │  Store)      │   │  Anthropic,  │
│   Audit)     │   │              │   │              │   │  etc.)       │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

---

## 6. Files Created

| File | Purpose |
|------|---------|
| `docs/security/SECURITY_ARCHITECTURE.md` | Complete security architecture design |
| `docs/security/API_MIDDLEWARE_DESIGN.md` | Middleware implementation details |
| `docs/security/DATABASE_SCHEMA_UPDATES.md` | Database schema changes |

---

## 7. Summary

The current Purple Team GPT architecture has several critical security vulnerabilities and design issues that must be addressed before production deployment:

**Critical Issues:**
1. No authentication or authorization
2. SSRF vulnerability via LLM endpoint configuration
3. Command injection risk in tool execution
4. WebSocket connections unauthenticated

**Design Improvements Needed:**
1. Replace global state with dependency injection
2. Add session persistence to database
3. Implement proper error handling
4. Add audit logging for security events

The proposed improvements follow industry best practices and will result in a production-ready, secure architecture.