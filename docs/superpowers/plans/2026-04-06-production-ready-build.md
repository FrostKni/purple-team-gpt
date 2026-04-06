# Purple Team GPT Production-Ready Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Purple Team GPT from ~70% complete to production-ready with user authentication, database persistence, complete LLM provider support (including Gemini), token management, caching, and 80%+ test coverage.

**Architecture:** FastAPI backend with PostgreSQL, Redis, ChromaDB. Multi-agent system with Red (offensive) and Blue (defensive) agents coordinated by an orchestrator. RAG pipeline for adaptive learning. React frontend with real-time WebSocket updates.

**Tech Stack:** Python 3.11, FastAPI, React/TypeScript, PostgreSQL, Redis, ChromaDB, LiteLLM, Docker Compose

---

## File Structure

### New Files to Create

```
purple-team-gpt/
├── src/purple_team_gpt/
│   ├── backend/
│   │   ├── routers/
│   │   │   ├── auth.py              # Authentication endpoints
│   │   │   └── users.py             # User management endpoints
│   │   └── middleware/
│   │       └── __init__.py
│   ├── core/
│   │   └── llm/
│   │       ├── budget.py            # Token budget management
│   │       └── cache.py             # Response caching
│   ├── agents/
│   │   └── memory.py                # Agent memory persistence
│   └── tools/
│       └── parsers.py               # Tool output parsers
├── tests/
│   ├── test_auth.py                 # Authentication tests
│   ├── test_users.py                # User management tests
│   ├── test_llm_budget.py           # Token budget tests
│   ├── test_llm_cache.py            # Response cache tests
│   ├── test_agent_memory.py         # Memory persistence tests
│   └── test_tool_parsers.py         # Parser tests
├── alembic/
│   └── versions/
│       └── 001_initial_schema.py    # Initial migration
└── docs/
    ├── API.md                       # API documentation
    └── QUICKSTART.md                # Setup guide
```

### Files to Modify

```
├── src/purple_team_gpt/
│   ├── config.py                    # Add Gemini config, validation
│   ├── backend/
│   │   └── main.py                  # Include new routers
│   ├── core/
│   │   ├── llm/
│   │   │   └── engine.py            # Add Gemini, budget, cache
│   │   └── orchestrator.py          # Wire to database, add memory
│   └── db/
│       └── database.py              # Ensure proper initialization
├── .env.example                     # Add new environment variables
└── docker-compose.yml               # Verify all services
```

---

## Phase 1: User Authentication System

### Task 1.1: Create Authentication Router

**Files:**
- Create: `src/purple_team_gpt/backend/routers/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write the failing test for user registration**

```python
# tests/test_auth.py
"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from purple_team_gpt.backend.main import app


@pytest.mark.asyncio
async def test_register_user():
    """Test user registration creates new user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "full_name": "Test User"
            }
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data
    assert "password" not in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd purple-team-gpt && pytest tests/test_auth.py::test_register_user -v`
Expected: FAIL with 404 or ImportError

- [ ] **Step 3: Create auth router with registration endpoint**

```python
# src/purple_team_gpt/backend/routers/auth.py
"""Authentication endpoints."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from purple_team_gpt.db.database import get_db
from purple_team_gpt.db.models import User
from purple_team_gpt.backend.security import (
    get_password_hash,
    create_access_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id}
    )
    
    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd purple-team-gpt && pytest tests/test_auth.py::test_register_user -v`
Expected: PASS

- [ ] **Step 5: Write test for login endpoint**

```python
# tests/test_auth.py (add to existing file)

@pytest.mark.asyncio
async def test_login_user():
    """Test user login returns valid token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!",
                "full_name": "Login User"
            }
        )
        
        # Then login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password():
    """Test login with wrong password fails."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "CorrectPass123!",
            }
        )
        
        # Try with wrong password
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPass123!"
            }
        )
    
    assert response.status_code == 401
```

- [ ] **Step 6: Add login endpoint to auth router**

```python
# src/purple_team_gpt/backend/routers/auth.py (add to existing file)

class UserLogin(BaseModel):
    email: EmailStr
    password: str


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return token."""
    # Find user
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    from purple_team_gpt.backend.security import verify_password
    
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id}
    )
    
    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd purple-team-gpt && pytest tests/test_auth.py -v`
Expected: All tests PASS

- [ ] **Step 8: Add get current user endpoint**

```python
# src/purple_team_gpt/backend/routers/auth.py (add to existing file)

from purple_team_gpt.backend.security import get_current_user


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user."""
    return UserResponse.model_validate(current_user)
```

- [ ] **Step 9: Write test for get current user**

```python
# tests/test_auth.py (add to existing file)

@pytest.mark.asyncio
async def test_get_current_user():
    """Test getting current user info."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register and login
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "me@example.com",
                "password": "SecurePass123!",
            }
        )
        token = register_response.json()["access_token"]
        
        # Get current user
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized():
    """Test getting current user without token fails."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")
    
    assert response.status_code == 401
```

- [ ] **Step 10: Run tests**

Run: `cd purple-team-gpt && pytest tests/test_auth.py -v`
Expected: All tests PASS

- [ ] **Step 11: Commit auth router**

```bash
cd purple-team-gpt
git add src/purple_team_gpt/backend/routers/auth.py tests/test_auth.py
git commit -m "feat(auth): add user registration, login, and /me endpoints"
```

---

### Task 1.2: Create Users Router

**Files:**
- Create: `src/purple_team_gpt/backend/routers/users.py`
- Create: `tests/test_users.py`

- [ ] **Step 1: Write the failing test for list users**

```python
# tests/test_users.py
"""Tests for user management endpoints."""

import pytest
from httpx import AsyncClient
from purple_team_gpt.backend.main import app


@pytest.mark.asyncio
async def test_list_users_as_admin():
    """Test admin can list all users."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create admin user and get token
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123!",
                "full_name": "Admin User"
            }
        )
        token = register_response.json()["access_token"]
        
        # List users
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
```

- [ ] **Step 2: Create users router**

```python
# src/purple_team_gpt/backend/routers/users.py
"""User management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from purple_team_gpt.db.database import get_db
from purple_team_gpt.db.models import User
from purple_team_gpt.backend.security import get_current_user
from purple_team_gpt.backend.routers.auth import UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users (requires authentication)."""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.model_validate(user)
```

- [ ] **Step 3: Run tests**

Run: `cd purple-team-gpt && pytest tests/test_users.py -v`
Expected: Tests PASS

- [ ] **Step 4: Commit users router**

```bash
cd purple-team-gpt
git add src/purple_team_gpt/backend/routers/users.py tests/test_users.py
git commit -m "feat(users): add user management endpoints"
```

---

### Task 1.3: Include New Routers in Main App

**Files:**
- Modify: `src/purple_team_gpt/backend/main.py`

- [ ] **Step 1: Add imports and include routers**

Find the router imports section in `src/purple_team_gpt/backend/main.py` and add:

```python
# Add to imports
from purple_team_gpt.backend.routers import auth, users
```

Then find where routers are included and add:

```python
# Add after other router includes
app.include_router(auth.router)
app.include_router(users.router)
```

- [ ] **Step 2: Verify routers are accessible**

Run: `cd purple-team-gpt && python -c "from purple_team_gpt.backend.main import app; print([r.path for r in app.routes if hasattr(r, 'path')])" | grep -E "(auth|users)"`
Expected: Shows auth and user routes

- [ ] **Step 3: Commit**

```bash
cd purple-team-gpt
git add src/purple_team_gpt/backend/main.py
git commit -m "feat: include auth and users routers in main app"
```

---

## Phase 2: Database Migration

### Task 2.1: Create Initial Database Migration

**Files:**
- Create: `alembic/versions/001_initial_schema.py`

- [ ] **Step 1: Verify Alembic is configured**

Run: `cd purple-team-gpt && ls -la alembic/`
Expected: Shows alembic.ini, env.py, versions/

- [ ] **Step 2: Generate initial migration**

Run: `cd purple-team-gpt && alembic revision --autogenerate -m "Initial schema"`
Expected: Creates new migration file

- [ ] **Step 3: Review generated migration**

Open the generated file and verify it includes all tables from `db/models.py`:
- users
- roles
- permissions
- user_roles
- role_permissions
- organizations
- organization_members
- authorized_targets
- sessions
- findings
- events
- audit_logs
- feedback

- [ ] **Step 4: Apply migration**

Run: `cd purple-team-gpt && alembic upgrade head`
Expected: "Running upgrade ... -> head"

- [ ] **Step 5: Verify tables exist**

Run: `cd purple-team-gpt && python -c "from purple_team_gpt.db.database import engine; import asyncio; async def check(): async with engine.begin() as conn: result = await conn.run_sync(lambda sync_conn: sync_conn.execute('SELECT tablename FROM pg_tables WHERE schemaname = '\''public'\'' ')); print([r[0] for r in result]); asyncio.run(check())"`
Expected: Lists all tables

- [ ] **Step 6: Commit migration**

```bash
cd purple-team-gpt
git add alembic/versions/
git commit -m "feat(db): add initial database migration"
```

---

### Task 2.2: Wire Orchestrator to Database

**Files:**
- Modify: `src/purple_team_gpt/core/orchestrator.py`

- [ ] **Step 1: Find persistence code in orchestrator**

Run: `cd purple-team-gpt && grep -n "persist_session" src/purple_team_gpt/core/orchestrator.py`
Note the line numbers

- [ ] **Step 2: Improve error handling in persistence**

Find the `_persist_session_create` method and update it:

```python
# In src/purple_team_gpt/core/orchestrator.py
# Find the _persist_session_create method and update:

async def _persist_session_create(self, session: SimulationSession) -> None:
    """Persist session creation to database with proper error handling."""
    if not self.session_repository:
        logger.debug("No database repository configured, skipping persistence")
        return
    
    try:
        # Create session record
        await self.session_repository.create_session(
            session_id=session.id,
            target=session.target,
            scope=session.scope or "",
            status=session.status.value,
        )
        logger.info(f"Session {session.id} persisted to database")
    except Exception as e:
        logger.error(f"Failed to persist session creation: {e}")
        # Session continues in-memory, database sync can retry later
```

- [ ] **Step 3: Add database flag to orchestrator init**

```python
# In orchestrator __init__ method, add use_database parameter:
def __init__(
    self,
    engine: LLMEngine,
    vector_store: VectorStore,
    session_repository: Optional[SessionRepository] = None,
    on_event: Optional[Callable[[AgentEvent], None]] = None,
):
    self.engine = engine
    self.vector_store = vector_store
    self.session_repository = session_repository
    self.use_database = session_repository is not None
    # ... rest of init
```

- [ ] **Step 4: Update main.py to pass repository**

In `src/purple_team_gpt/backend/main.py`, update orchestrator initialization:

```python
# In the lifespan function, after database initialization:
from purple_team_gpt.db.repository import SessionRepository

# When creating orchestrator:
if db_initialized:
    session_repository = SessionRepository(db_session)
else:
    session_repository = None

orchestrator = PurpleOrchestrator(
    engine=llm_engine,
    vector_store=vector_store,
    session_repository=session_repository,
)
```

- [ ] **Step 5: Test session persistence**

Run: `cd purple-team-gpt && pytest tests/test_orchestrator.py -v -k "session"`
Expected: Tests pass

- [ ] **Step 6: Commit**

```bash
cd purple-team-gpt
git add src/purple_team_gpt/core/orchestrator.py src/purple_team_gpt/backend/main.py
git commit -m "feat(orchestrator): wire database persistence with error handling"
```

---

## Phase 3: LLM Provider Integration

### Task 3.1: Add Gemini Provider Support

**Files:**
- Modify: `src/purple_team_gpt/config.py`
- Modify: `src/purple_team_gpt/core/llm/engine.py`
- Create: `tests/test_llm_gemini.py`

- [ ] **Step 1: Add Gemini configuration**

In `src/purple_team_gpt/config.py`, find `LLMSettings` class and add:

```python
# In LLMSettings class
gemini_api_key: Optional[str] = None
```

- [ ] **Step 2: Add Gemini to provider enum**

In `src/purple_team_gpt/core/llm/engine.py`, find `Provider` enum and add:

```python
class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    GEMINI = "gemini"  # NEW
```

- [ ] **Step 3: Add Gemini to failover order**

In `LLMEngine._get_failover_order` method, add:

```python
def _get_failover_order(self) -> List[Provider]:
    order = []
    if self.settings.openai_api_key:
        order.append(Provider.OPENAI)
    if self.settings.anthropic_api_key:
        order.append(Provider.ANTHROPIC)
    if self.settings.gemini_api_key:
        order.append(Provider.GEMINI)  # NEW
    if self.settings.groq_api_key:
        order.append(Provider.GROQ)
    if self.settings.deepseek_api_key:
        order.append(Provider.DEEPSEEK)
    if self.settings.mistral_api_key:
        order.append(Provider.MISTRAL)
    order.append(Provider.OLLAMA)
    return order
```

- [ ] **Step 4: Add Gemini models to provider models**

In `LLMEngine.PROVIDER_MODELS`, add:

```python
PROVIDER_MODELS = {
    # ... existing providers
    Provider.GEMINI: ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
}
```

- [ ] **Step 5: Write test for Gemini integration**

```python
# tests/test_llm_gemini.py
"""Tests for Gemini provider integration."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from purple_team_gpt.core.llm.engine import LLMEngine, Provider
from purple_team_gpt.config import LLMSettings


def test_gemini_in_failover_order():
    """Test Gemini is included in failover when API key present."""
    settings = LLMSettings(
        gemini_api_key="test-key",
        default_provider="gemini",
    )
    engine = LLMEngine(settings)
    
    assert Provider.GEMINI in engine._failover_order


@pytest.mark.asyncio
async def test_gemini_model_string_format():
    """Test Gemini model string is correctly formatted for LiteLLM."""
    settings = LLMSettings(
        gemini_api_key="test-key",
        default_model="gemini-2.0-flash",
    )
    engine = LLMEngine(settings)
    
    model_string = engine._get_model_string(Provider.GEMINI, "gemini-2.0-flash")
    assert model_string == "gemini/gemini-2.0-flash"
```

- [ ] **Step 6: Run tests**

Run: `cd purple-team-gpt && pytest tests/test_llm_gemini.py -v`
Expected: Tests PASS

- [ ] **Step 7: Commit**

```bash
cd purple-team-gpt
git add src/purple_team_gpt/config.py src/purple_team_gpt/core/llm/engine.py tests/test_llm_gemini.py
git commit -m "feat(llm): add Gemini provider support"
```

---

### Task 3.2: Implement Token Budget Management

**Files:**
- Create: `src/purple_team_gpt/core/llm/budget.py`
- Create: `tests/test_llm_budget.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_budget.py
"""Tests for token budget management."""

import pytest
from purple_team_gpt.core.llm.budget import TokenBudget


def test_count_tokens_estimation():
    """Test token counting estimation."""
    budget = TokenBudget(provider="openai", model="gpt-4o")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    
    count = budget.count_tokens(messages)
    # Rough estimation: ~4 chars per token
    assert count > 0
    assert count < 100


def test_check_budget_within_limits():
    """Test budget check passes for small messages."""
    budget = TokenBudget(provider="openai", model="gpt-4o")
    
    messages = [{"role": "user", "content": "Hello!"}]
    
    assert budget.check_budget(messages) is True


def test_check_budget_exceeds_limits():
    """Test budget check fails for messages exceeding context window."""
    budget = TokenBudget(provider="openai", model="gpt-4o")
    
    # Create very large message
    large_content = "x" * 1000000  # 1M characters
    messages = [{"role": "user", "content": large_content}]
    
    assert budget.check_budget(messages) is False


def test_truncate_messages():
    """Test message truncation to fit budget."""
    budget = TokenBudget(provider="openai", model="gpt-4o", max_context_tokens=100)
    
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "a" * 10000},  # Large message
    ]
    
    truncated = budget.truncate_messages(messages)
    
    # System prompt should be preserved
    assert truncated[0]["role"] == "system"
    # Total should fit budget
    assert budget.check_budget(truncated)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd purple-team-gpt && pytest tests/test_llm_budget.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement TokenBudget class**

```python
# src/purple_team_gpt/core/llm/budget.py
"""Token budget management for LLM context windows."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TokenBudget:
    """Prevent context window overflow and manage token costs."""
    
    PROVIDER_LIMITS: Dict[str, Dict[str, int]] = {
        "openai": {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4-turbo": 128000,
            "o1": 200000,
            "o3-mini": 200000,
        },
        "anthropic": {
            "claude-sonnet-4-20250514": 200000,
            "claude-opus-4-20250514": 200000,
            "claude-3-5-haiku-20241022": 200000,
        },
        "gemini": {
            "gemini-2.0-flash": 1000000,
            "gemini-1.5-pro": 2000000,
            "gemini-1.5-flash": 1000000,
        },
        "groq": {
            "llama-3.3-70b-versatile": 128000,
            "mixtral-8x7b-32768": 32768,
        },
        "ollama": {
            "llama3.2": 128000,
            "mistral": 32000,
            "codellama": 16000,
        },
    }
    
    def __init__(
        self,
        provider: str,
        model: str,
        max_context_tokens: Optional[int] = None,
        reserved_for_response: int = 4096
    ):
        self.provider = provider.lower()
        self.model = model
        self.max_context_tokens = max_context_tokens or self._get_default_limit()
        self.reserved_for_response = reserved_for_response
        self.available_for_input = self.max_context_tokens - self.reserved_for_response
    
    def _get_default_limit(self) -> int:
        """Get default context limit for provider/model."""
        provider_limits = self.PROVIDER_LIMITS.get(self.provider, {})
        return provider_limits.get(self.model, 4096)
    
    def count_tokens(self, messages: List[Dict]) -> int:
        """Estimate token count for messages.
        
        Uses rough estimation: ~4 characters per token for English text.
        For production, consider using tiktoken for OpenAI models.
        """
        total_chars = 0
        for message in messages:
            # Count role and content
            total_chars += len(message.get("role", ""))
            total_chars += len(message.get("content", ""))
            # Add overhead for message formatting
            total_chars += 4  # Approximate overhead per message
        
        # Rough estimation: 4 chars per token
        return total_chars // 4
    
    def check_budget(self, messages: List[Dict]) -> bool:
        """Check if messages fit within token budget."""
        count = self.count_tokens(messages)
        return count <= self.available_for_input
    
    def truncate_messages(
        self,
        messages: List[Dict],
        preserve_system: bool = True
    ) -> List[Dict]:
        """Truncate messages to fit budget while preserving important context.
        
        Args:
            messages: List of message dicts
            preserve_system: If True, always keep system prompt
        
        Returns:
            Truncated list of messages that fits budget
        """
        if self.check_budget(messages):
            return messages
        
        result = []
        system_messages = []
        
        # Extract system messages if preserving
        if preserve_system:
            system_messages = [m for m in messages if m.get("role") == "system"]
            other_messages = [m for m in messages if m.get("role") != "system"]
        else:
            other_messages = messages.copy()
        
        # Calculate space for system messages
        system_tokens = self.count_tokens(system_messages)
        available_for_other = self.available_for_input - system_tokens
        
        # Add messages from most recent to oldest until budget exhausted
        current_tokens = 0
        reversed_other = list(reversed(other_messages))
        
        for message in reversed_other:
            msg_tokens = self.count_tokens([message])
            if current_tokens + msg_tokens <= available_for_other:
                result.insert(0, message)
                current_tokens += msg_tokens
            else:
                break
        
        return system_messages + result
```

- [ ] **Step 4: Run tests**

Run: `cd purple-team-gpt && pytest tests/test_llm_budget.py -v`
Expected: All tests PASS

- [ ] **Step 5: Integrate TokenBudget into LLMEngine**

In `src/purple_team_gpt/core/llm/engine.py`, add budget checking:

```python
# Add import
from purple_team_gpt.core.llm.budget import TokenBudget

# In LLMEngine.__init__, add:
self.budget = TokenBudget(
    provider=settings.default_provider,
    model=settings.default_model
)

# In chat method, before API call:
def chat(self, conversation: Conversation, ...):
    messages = conversation.to_api_format()
    
    # Check budget and truncate if needed
    if not self.budget.check_budget(messages):
        logger.warning("Message history exceeds token budget, truncating")
        messages = self.budget.truncate_messages(messages)
    
    # Continue with API call...
```

- [ ] **Step 6: Commit**

```bash
cd purple-team-gpt
git add src/purple_team_gpt/core/llm/budget.py src/purple_team_gpt/core/llm/engine.py tests/test_llm_budget.py
git commit -m "feat(llm): add token budget management"
```

---

### Task 3.3: Implement Response Caching

**Files:**
- Create: `src/purple_team_gpt/core/llm/cache.py`
- Create: `tests/test_llm_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_cache.py
"""Tests for LLM response caching."""

import pytest
import time
from purple_team_gpt.core.llm.cache import SemanticCache


@pytest.mark.asyncio
async def test_cache_miss():
    """Test cache returns None for new prompt."""
    cache = SemanticCache()
    
    result = await cache.get_cached("What is 2+2?", [0.1, 0.2, 0.3])
    
    assert result is None


@pytest.mark.asyncio
async def test_cache_hit():
    """Test cache returns response for similar prompt."""
    cache = SemanticCache()
    
    prompt = "What is 2+2?"
    embedding = [0.1] * 128
    response = "2+2 equals 4"
    
    # Cache the response
    await cache.cache_response(prompt, embedding, response)
    
    # Retrieve it
    result = await cache.get_cached("What is 2+2?", embedding)
    
    assert result == response


@pytest.mark.asyncio
async def test_cache_expiry():
    """Test cache entries expire after TTL."""
    cache = SemanticCache(ttl=1)  # 1 second TTL
    
    prompt = "Test prompt"
    embedding = [0.1] * 128
    response = "Test response"
    
    await cache.cache_response(prompt, embedding, response)
    
    # Should be cached now
    result = await cache.get_cached(prompt, embedding)
    assert result == response
    
    # Wait for expiry
    time.sleep(2)
    
    # Should be expired
    result = await cache.get_cached(prompt, embedding)
    assert result is None


@pytest.mark.asyncio
async def test_cache_clear_expired():
    """Test clearing expired entries."""
    cache = SemanticCache(ttl=1)
    
    await cache.cache_response("prompt1", [0.1], "response1")
    await cache.cache_response("prompt2", [0.2], "response2")
    
    assert len(cache._cache) == 2
    
    time.sleep(2)
    await cache.clear_expired()
    
    assert len(cache._cache) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd purple-team-gpt && pytest tests/test_llm_cache.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement SemanticCache**

```python
# src/purple_team_gpt/core/llm/cache.py
"""Response caching for LLM API calls."""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached LLM response."""
    prompt_hash: str
    prompt: str
    embedding: List[float]
    response: str
    created_at: float = field(default_factory=time.time)
    ttl: int = 3600
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl


class SemanticCache:
    """Cache LLM responses by prompt similarity.
    
    For now, uses exact hash matching. In production, integrate with
    vector store for semantic similarity matching.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.95,
        ttl: int = 3600,
        max_size: int = 1000
    ):
        self.similarity_threshold = similarity_threshold
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, CachedResponse] = {}
    
    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash for prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    async def get_cached(
        self,
        prompt: str,
        embedding: Optional[List[float]] = None
    ) -> Optional[str]:
        """Return cached response if available and not expired.
        
        Args:
            prompt: The prompt text
            embedding: Optional embedding for semantic matching (not used yet)
        
        Returns:
            Cached response or None
        """
        prompt_hash = self._hash_prompt(prompt)
        
        cached = self._cache.get(prompt_hash)
        if cached is None:
            return None
        
        if cached.is_expired():
            del self._cache[prompt_hash]
            return None
        
        logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
        return cached.response
    
    async def cache_response(
        self,
        prompt: str,
        embedding: Optional[List[float]],
        response: str
    ) -> None:
        """Store response in cache.
        
        Args:
            prompt: The prompt text
            embedding: Optional embedding for semantic matching
            response: The LLM response to cache
        """
        prompt_hash = self._hash_prompt(prompt)
        
        # Enforce max size with LRU eviction
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        self._cache[prompt_hash] = CachedResponse(
            prompt_hash=prompt_hash,
            prompt=prompt,
            embedding=embedding or [],
            response=response,
            ttl=self.ttl
        )
        
        logger.debug(f"Cached response for prompt: {prompt[:50]}...")
    
    def _evict_oldest(self) -> None:
        """Remove oldest cache entry."""
        if not self._cache:
            return
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        del self._cache[oldest_key]
        logger.debug("Evicted oldest cache entry")
    
    async def clear_expired(self) -> int:
        """Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def clear_all(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        logger.info("Cleared all cache entries")
    
    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
```

- [ ] **Step 4: Run tests**

Run: `cd purple-team-gpt && pytest tests/test_llm_cache.py -v`
Expected: All tests PASS

- [ ] **Step 5: Integrate cache into LLMEngine**

In `src/purple_team_gpt/core/llm/engine.py`:

```python
# Add import
from purple_team_gpt.core.llm.cache import SemanticCache

# In LLMEngine.__init__, add:
self.cache = SemanticCache(ttl=settings.cache_ttl or 3600)

# In chat method, add cache check:
async def chat(self, conversation: Conversation, ...):
    messages = conversation.to_api_format()
    prompt = str(messages)  # Simple serialization
    
    # Check cache first
    cached = await self.cache.get_cached(prompt)
    if cached:
        logger.info("Returning cached response")
        return cached
    
    # ... existing API call logic ...
    response = await self._blocking_chat(model, messages)
    
    # Cache the response
    await self.cache.cache_response(prompt, None, response)
    
    return response
```

- [ ] **Step 6: Add cache_ttl to config**

In `src/purple_team_gpt/config.py`, in `LLMSettings`:

```python
cache_ttl: int = 3600  # Cache TTL in seconds
```

- [ ] **Step 7: Commit**

```bash
cd purple-team-gpt
git add src/purple_team_gpt/core/llm/cache.py src/purple_team_gpt/core/llm/engine.py src/purple_team_gpt/config.py tests/test_llm_cache.py
git commit -m "feat(llm): add response caching"
```

---

## Phase 4: Agent Memory Persistence

### Task 4.1: Implement Agent Memory System

**Files:**
- Create: `src/purple_team_gpt/agents/memory.py`
- Create: `tests/test_agent_memory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_memory.py
"""Tests for agent memory persistence."""

import pytest
from purple_team_gpt.agents.memory import AgentMemory, AgentLearning
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_vector_store():
    """Create mock vector store."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_save_session(mock_vector_store):
    """Test saving session state."""
    memory = AgentMemory(agent_id="test-agent", vector_store=mock_vector_store)
    
    state = {
        "target": "192.168.1.1",
        "findings": ["Open port 22"],
        "steps": 5
    }
    
    await memory.save_session("session-123", state)
    
    # Verify session was stored
    assert "session-123" in memory._sessions


@pytest.mark.asyncio
async def test_load_session(mock_vector_store):
    """Test loading session state."""
    memory = AgentMemory(agent_id="test-agent", vector_store=mock_vector_store)
    
    state = {"target": "192.168.1.1"}
    await memory.save_session("session-123", state)
    
    loaded = await memory.load_session("session-123")
    
    assert loaded == state


@pytest.mark.asyncio
async def test_load_nonexistent_session(mock_vector_store):
    """Test loading session that doesn't exist."""
    memory = AgentMemory(agent_id="test-agent", vector_store=mock_vector_store)
    
    loaded = await memory.load_session("nonexistent")
    
    assert loaded is None


@pytest.mark.asyncio
async def test_save_learning(mock_vector_store):
    """Test saving learning to vector store."""
    memory = AgentMemory(agent_id="red-agent", vector_store=mock_vector_store)
    
    learning = AgentLearning(
        pattern="SQL injection on target X",
        context="Web application with login form",
        success=True,
        tool_used="sqlmap"
    )
    
    await memory.save_learning(learning)
    
    # Verify vector store was called
    mock_vector_store.add.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd purple-team-gpt && pytest tests/test_agent_memory.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement AgentMemory**

```python
# src/purple_team_gpt/agents/memory.py
"""Agent memory persistence for learning across sessions."""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from purple_team_gpt.core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class AgentLearning:
    """A learned pattern or technique."""
    pattern: str
    context: str
    success: bool
    tool_used: Optional[str] = None
    outcome: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class AgentMemory:
    """Persist agent state and learnings across sessions.
    
    Uses two storage mechanisms:
    1. In-memory dict for session state (for development)
    2. Vector store for learnings (for semantic retrieval)
    
    In production, session state should be persisted to database.
    """
    
    def __init__(
        self,
        agent_id: str,
        vector_store: VectorStore,
        collection_name: str = "agent_memory"
    ):
        self.agent_id = agent_id
        self.vector_store = vector_store
        self.collection_name = collection_name
        self._sessions: Dict[str, Dict] = {}
    
    async def save_session(
        self,
        session_id: str,
        state: Dict[str, Any]
    ) -> None:
        """Save agent state at end of session.
        
        Args:
            session_id: Unique session identifier
            state: Agent state including target, findings, steps, etc.
        """
        self._sessions[session_id] = {
            **state,
            "agent_id": self.agent_id,
            "saved_at": datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"Agent {self.agent_id} saved session {session_id}: "
            f"{len(state.get('findings', []))} findings"
        )
    
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load previous session state.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Session state or None if not found
        """
        session = self._sessions.get(session_id)
        
        if session:
            logger.info(
                f"Agent {self.agent_id} loaded session {session_id}"
            )
        else:
            logger.debug(
                f"Agent {self.agent_id} session {session_id} not found"
            )
        
        return session
    
    async def save_learning(self, learning: AgentLearning) -> None:
        """Store a learned pattern for future use.
        
        Args:
            learning: The learning to store
        """
        # Create document for vector store
        document = f"""
Pattern: {learning.pattern}
Context: {learning.context}
Success: {learning.success}
Tool: {learning.tool_used or 'N/A'}
Outcome: {learning.outcome or 'N/A'}
        """.strip()
        
        # Store in vector store
        await self.vector_store.add(
            collection_name=self.collection_name,
            documents=[document],
            metadatas=[{
                "agent_id": self.agent_id,
                "pattern": learning.pattern,
                "success": learning.success,
                "tool": learning.tool_used or "",
                "timestamp": learning.timestamp.isoformat()
            }]
        )
        
        logger.info(
            f"Agent {self.agent_id} saved learning: "
            f"{learning.pattern[:50]}..."
        )
    
    async def get_relevant_learnings(
        self,
        context: str,
        n_results: int = 5
    ) -> List[AgentLearning]:
        """Retrieve learnings relevant to current context.
        
        Args:
            context: Current situation description
            n_results: Maximum number of learnings to return
        
        Returns:
            List of relevant learnings
        """
        try:
            results = await self.vector_store.query(
                collection_name=self.collection_name,
                query_text=context,
                n_results=n_results,
                where={"agent_id": self.agent_id}
            )
            
            learnings = []
            for doc, meta in zip(
                results.get("documents", []),
                results.get("metadatas", [])
            ):
                learnings.append(AgentLearning(
                    pattern=meta.get("pattern", ""),
                    context=doc,
                    success=meta.get("success", False),
                    tool_used=meta.get("tool"),
                ))
            
            logger.info(
                f"Agent {self.agent_id} retrieved {len(learnings)} "
                f"relevant learnings"
            )
            
            return learnings
            
        except Exception as e:
            logger.warning(f"Failed to retrieve learnings: {e}")
            return []
    
    def clear_sessions(self) -> None:
        """Clear all stored sessions (for testing)."""
        self._sessions.clear()
        logger.info(f"Agent {self.agent_id} cleared all sessions")
```

- [ ] **Step 4: Run tests**

Run: `cd purple-team-gpt && pytest tests/test_agent_memory.py -v`
Expected: All tests PASS

- [ ] **Step 5: Integrate memory into base agent**

In `src/purple_team_gpt/agents/base.py`, add memory support:

```python
# Add import
from purple_team_gpt.agents.memory import AgentMemory, AgentLearning

# In BaseAgent.__init__, add:
def __init__(
    self,
    engine: LLMEngine,
    vector_store: VectorStore,
    memory: Optional[AgentMemory] = None,
    ...
):
    self.memory = memory
    # ... rest of init

# Add method to query memory:
async def query_memory(self, context: str) -> List[AgentLearning]:
    """Query agent memory for relevant learnings."""
    if not self.memory:
        return []
    return await self.memory.get_relevant_learnings(context)
```

- [ ] **Step 6: Commit**

```bash
cd purple-team-gpt
git add src/purple_team_gpt/agents/memory.py src/purple_team_gpt/agents/base.py tests/test_agent_memory.py
git commit -m "feat(agents): add memory persistence for learning"
```

---

## Phase 5: Frontend Error Boundaries

### Task 5.1: Create Error Boundary Component

**Files:**
- Create: `src/frontend/src/components/ErrorBoundary.tsx`

- [ ] **Step 1: Check frontend structure**

Run: `ls -la purple-team-gpt/src/frontend/src/components/`
Expected: Shows existing components

- [ ] **Step 2: Create ErrorBoundary component**

```typescript
// src/frontend/src/components/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={this.handleReset}>
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

- [ ] **Step 3: Add CSS styles**

In `src/frontend/src/index.css` or relevant CSS file, add:

```css
.error-boundary {
  padding: 2rem;
  text-align: center;
  background-color: #fef2f2;
  border: 1px solid #ef4444;
  border-radius: 0.5rem;
  margin: 1rem;
}

.error-boundary h2 {
  color: #dc2626;
  margin-bottom: 1rem;
}

.error-boundary p {
  color: #7f1d1d;
  margin-bottom: 1rem;
}

.error-boundary button {
  padding: 0.5rem 1rem;
  background-color: #dc2626;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

.error-boundary button:hover {
  background-color: #b91c1c;
}
```

- [ ] **Step 4: Wrap main app with ErrorBoundary**

In `src/frontend/src/App.tsx`, wrap the main content:

```typescript
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      {/* Existing app content */}
    </ErrorBoundary>
  );
}
```

- [ ] **Step 5: Test frontend builds**

Run: `cd purple-team-gpt/src/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
cd purple-team-gpt
git add src/frontend/src/components/ErrorBoundary.tsx src/frontend/src/App.tsx src/frontend/src/index.css
git commit -m "feat(frontend): add error boundary for graceful error handling"
```

---

## Phase 6: Testing and Documentation

### Task 6.1: Increase Test Coverage

**Files:**
- Create: `tests/integration/test_full_session.py`

- [ ] **Step 1: Run coverage report**

Run: `cd purple-team-gpt && pytest --cov=src/purple_team_gpt --cov-report=term-missing`
Expected: Shows current coverage ~44%

- [ ] **Step 2: Write integration test for full session flow**

```python
# tests/integration/test_full_session.py
"""Integration tests for complete session flows."""

import pytest
from httpx import AsyncClient
from purple_team_gpt.backend.main import app


@pytest.mark.asyncio
async def test_full_session_workflow():
    """Test complete session lifecycle: create, start, monitor, stop."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Register and login
        auth_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "integration@example.com",
                "password": "TestPass123!"
            }
        )
        assert auth_response.status_code == 201
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create session
        create_response = await client.post(
            "/api/v1/sessions/",
            json={
                "target": "127.0.0.1",
                "scope": "Local test target"
            },
            headers=headers
        )
        assert create_response.status_code == 201
        session_id = create_response.json()["id"]
        
        # 3. Get session status
        status_response = await client.get(
            f"/api/v1/sessions/{session_id}",
            headers=headers
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "pending"
        
        # 4. Start session
        start_response = await client.post(
            f"/api/v1/sessions/{session_id}/start",
            headers=headers
        )
        assert start_response.status_code == 200
        
        # 5. Stop session
        stop_response = await client.post(
            f"/api/v1/sessions/{session_id}/stop",
            headers=headers
        )
        assert stop_response.status_code == 200
        
        # 6. Get final report
        report_response = await client.get(
            f"/api/v1/sessions/{session_id}/report",
            headers=headers
        )
        assert report_response.status_code == 200


@pytest.mark.asyncio
async def test_session_persistence():
    """Test that session data persists correctly."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create authenticated user
        auth_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "persist@example.com",
                "password": "TestPass123!"
            }
        )
        token = auth_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create and start session
        create_response = await client.post(
            "/api/v1/sessions/",
            json={"target": "test.local"},
            headers=headers
        )
        session_id = create_response.json()["id"]
        
        # Retrieve session
        get_response = await client.get(
            f"/api/v1/sessions/{session_id}",
            headers=headers
        )
        
        assert get_response.json()["target"] == "test.local"
```

- [ ] **Step 3: Run new tests**

Run: `cd purple-team-gpt && pytest tests/integration/test_full_session.py -v`
Expected: Tests PASS

- [ ] **Step 4: Commit**

```bash
cd purple-team-gpt
git add tests/integration/test_full_session.py
git commit -m "test: add integration tests for full session workflow"
```

---

### Task 6.2: Create API Documentation

**Files:**
- Create: `docs/API.md`

- [ ] **Step 1: Create API documentation**

```markdown
# docs/API.md
# Purple Team GPT API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints (except registration and login) require JWT authentication.

```http
Authorization: Bearer <access_token>
```

---

## Authentication Endpoints

### Register User

```http
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true
  }
}
```

### Login

```http
POST /auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {...}
}
```

### Get Current User

```http
GET /auth/me
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true
}
```

---

## Session Endpoints

### Create Session

```http
POST /sessions/
```

**Request Body:**
```json
{
  "target": "192.168.1.100",
  "scope": "Penetration test for web application"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid-string",
  "target": "192.168.1.100",
  "status": "pending",
  "created_at": "2026-04-06T12:00:00Z"
}
```

### List Sessions

```http
GET /sessions/?skip=0&limit=100
```

**Response:** `200 OK`
```json
[
  {
    "id": "uuid-string",
    "target": "192.168.1.100",
    "status": "completed",
    ...
  }
]
```

### Get Session

```http
GET /sessions/{session_id}
```

**Response:** `200 OK`
```json
{
  "id": "uuid-string",
  "target": "192.168.1.100",
  "status": "running",
  "red_findings": [...],
  "blue_findings": [...],
  ...
}
```

### Start Session

```http
POST /sessions/{session_id}/start
```

**Response:** `200 OK`

### Stop Session

```http
POST /sessions/{session_id}/stop
```

**Response:** `200 OK`

### Get Session Report

```http
GET /sessions/{session_id}/report
```

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "target": "192.168.1.100",
  "duration": "00:15:30",
  "red_findings": [
    {
      "title": "Open SSH Port",
      "severity": "Medium",
      "description": "SSH service exposed on port 22",
      ...
    }
  ],
  "blue_findings": [...],
  "metrics": {...}
}
```

---

## WebSocket Events

Connect to: `ws://localhost:8000/ws/session/{session_id}`

### Events

**Agent Step:**
```json
{
  "type": "step",
  "agent": "red",
  "data": {
    "step_num": 1,
    "action": "execute",
    "tool": "nmap",
    "success": true
  }
}
```

**Finding:**
```json
{
  "type": "finding",
  "agent": "red",
  "data": {
    "title": "SQL Injection",
    "severity": "High",
    ...
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

### Common Status Codes

- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
```

- [ ] **Step 2: Commit**

```bash
cd purple-team-gpt
git add docs/API.md
git commit -m "docs: add comprehensive API documentation"
```

---

### Task 6.3: Create Quickstart Guide

**Files:**
- Create: `docs/QUICKSTART.md`

- [ ] **Step 1: Create quickstart guide**

```markdown
# docs/QUICKSTART.md
# Purple Team GPT Quick Start Guide

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)
- At least one LLM API key (OpenAI, Anthropic, or Gemini)

## Quick Start with Docker

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/purple-team-gpt
cd purple-team-gpt
cp .env.example .env
```

### 2. Set API Keys

Edit `.env` and add your API keys:

```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
GEMINI_API_KEY=AIza-your-key-here
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 5. Create Account

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "Test User"
  }'
```

## Local Development Setup

### Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start development server
uvicorn purple_team_gpt.backend.main:app --reload
```

### Frontend

```bash
cd src/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Running Your First Assessment

### 1. Create a Session

Via API:
```bash
curl -X POST http://localhost:8000/api/v1/sessions/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "127.0.0.1",
    "scope": "Local test assessment"
  }'
```

Or via UI:
1. Navigate to Attack Dashboard
2. Enter target IP/hostname
3. Click "Create Session"

### 2. Start the Assessment

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Monitor Progress

Connect to WebSocket:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session/{session_id}');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

Or watch the real-time dashboard in the UI.

### 4. Review Results

```bash
curl http://localhost:8000/api/v1/sessions/{session_id}/report \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Configuration Options

### LLM Providers

Set `DEFAULT_LLM_PROVIDER` and `DEFAULT_MODEL` in `.env`:

```bash
# OpenAI (recommended)
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4o

# Anthropic
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-sonnet-4-20250514

# Gemini
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_MODEL=gemini-2.0-flash

# Local (Ollama)
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

### Agent Settings

```bash
AGENT_MAX_STEPS=50          # Maximum steps per agent
AGENT_TIMEOUT=300           # Timeout in seconds
AGENT_SAFE_MODE=true        # Disable destructive operations
AGENT_MEMORY_ENABLED=true   # Enable learning persistence
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

### LLM API Errors

1. Verify API key is correct
2. Check rate limits
3. Try a different provider

```bash
# Test provider health
curl http://localhost:8000/api/v1/llm/health
```

### ChromaDB Issues

```bash
# Check ChromaDB status
curl http://localhost:8001/api/v1/heartbeat

# Reset vector store
rm -rf ./data/chromadb
```

## Next Steps

- Read the [API Documentation](API.md)
- Learn about [Architecture](ARCHITECTURE.md)
- Join the community discussions
- Report issues on GitHub
```

- [ ] **Step 2: Commit**

```bash
cd purple-team-gpt
git add docs/QUICKSTART.md
git commit -m "docs: add quick start guide for new users"
```

---

## Final Integration

### Task 7.1: Run Full Test Suite

- [ ] **Step 1: Run all tests with coverage**

Run: `cd purple-team-gpt && pytest --cov=src/purple_team_gpt --cov-report=html --cov-report=term`
Expected: Coverage >= 80%

- [ ] **Step 2: Fix any failing tests**

If tests fail, investigate and fix.

- [ ] **Step 3: Generate coverage badge**

Note the coverage percentage for documentation.

---

### Task 7.2: Verify End-to-End Flow

- [ ] **Step 1: Start all services**

Run: `cd purple-team-gpt && docker-compose up -d`

- [ ] **Step 2: Verify services are healthy**

Run: `cd purple-team-gpt && docker-compose ps`
Expected: All services "healthy"

- [ ] **Step 3: Test user registration**

Run: `curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"Test123!"}'`
Expected: 201 response with token

- [ ] **Step 4: Test session creation**

Use the token to create a session and verify it persists.

- [ ] **Step 5: Test WebSocket connection**

Connect to WebSocket and verify events are received.

---

### Task 7.3: Final Commit and Push

- [ ] **Step 1: Ensure all changes committed**

Run: `cd purple-team-gpt && git status`
Expected: No uncommitted changes

- [ ] **Step 2: Push to remote**

Run: `cd purple-team-gpt && git push origin main`

---

## Success Criteria

After completing this plan, verify:

- [ ] User can register and login
- [ ] Sessions persist across backend restarts
- [ ] All LLM providers (OpenAI, Anthropic, Gemini, Groq, Ollama) work
- [ ] Token budget prevents context overflow
- [ ] Response cache reduces API calls
- [ ] Agent memory persists learnings
- [ ] Test coverage >= 80%
- [ ] API documentation complete
- [ ] Quickstart guide accurate
- [ ] All services healthy in Docker Compose
- [ ] WebSocket real-time updates work
