# Purple Team GPT - Production-Ready Build Design

**Date:** 2026-04-06  
**Goal:** Build production-ready Purple Team GPT with complete multi-provider LLM support for local development deployment.

---

## Executive Summary

This design document outlines the plan to transform Purple Team GPT from its current ~70% complete state to a production-ready system. The focus is on completing critical missing components, integrating all major LLM providers (including Gemini), and achieving 80%+ test coverage.

**Timeline:** 3-4 weeks  
**Deployment Target:** Local development with Docker Compose  
**Primary Users:** Security professionals running offensive/defensive simulations

---

## Current State Analysis

### What's Working (Don't Change)

| Component | Status | Location |
|-----------|--------|----------|
| Multi-provider LLM engine | ✅ Excellent | `core/llm/engine.py` |
| Red Agent implementation | ✅ Complete | `agents/red_agent.py` |
| Blue Agent implementation | ✅ Complete | `agents/blue_agent.py` |
| RAG pipeline with ChromaDB | ✅ Working | `core/rag/` |
| WebSocket real-time updates | ✅ Functional | `routers/websocket.py` |
| Docker Compose setup | ✅ Ready | `docker-compose.yml` |
| Database schema | ✅ Excellent | `db/models.py` |

### What's Missing (Must Build)

| Component | Impact | Priority |
|-----------|--------|----------|
| User authentication endpoints | Blocks usage | P0 |
| Database migrations | Sessions don't persist | P0 |
| Gemini provider integration | Missing provider | P1 |
| Token budget management | API failures | P1 |
| Response caching | Cost/latency | P1 |
| Agent memory persistence | No learning | P1 |
| Tool output parsers | Inefficient | P2 |
| Test coverage (44% → 80%) | Quality risk | P1 |
| API documentation | Usability | P2 |

---

## Architecture Design

### System Components

```
┌────────────────────────────────────────────────────────────────────┐
│                      REACT FRONTEND                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Attack     │  │   Defense    │  │  Learning    │             │
│  │  Dashboard   │  │  Dashboard   │  │  Dashboard   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│  NEW: Error Boundaries, Provider Health Dashboard                  │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Sessions   │  │  WebSocket   │  │   Feedback   │             │
│  │    ✅        │  │    ✅        │  │    ✅        │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│  NEW: Users Router, Auth Router, Organizations Router              │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                    CORE SERVICES                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   LLM ENGINE                                  │  │
│  │  OpenAI │ Anthropic │ Gemini │ Groq │ Ollama │ ...          │  │
│  │  NEW: Token Budget │ Response Cache │ Provider Health       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   RAG PIPELINE                                │  │
│  │  ChromaDB │ Embeddings │ Vector Store                        │  │
│  │  NEW: Embedding Cache                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   AGENT COORDINATION                          │  │
│  │  Orchestrator │ Red Agent │ Blue Agent                       │  │
│  │  NEW: Agent Memory Persistence                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  PostgreSQL  │  │   ChromaDB   │  │    Redis     │             │
│  │ NEW: Migrate │  │    ✅        │  │    ✅        │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Design

### 1. User Authentication System

**Files to Create:**
- `src/purple_team_gpt/backend/routers/users.py`
- `src/purple_team_gpt/backend/routers/auth.py`

**API Endpoints:**

```
POST   /api/v1/auth/register     # Create new user
POST   /api/v1/auth/login        # Authenticate, return JWT
POST   /api/v1/auth/refresh      # Refresh access token
POST   /api/v1/auth/logout       # Invalidate refresh token
GET    /api/v1/auth/me           # Get current user info

GET    /api/v1/users/            # List users (admin)
GET    /api/v1/users/{id}        # Get user by ID (admin)
PUT    /api/v1/users/{id}        # Update user (admin)
DELETE /api/v1/users/{id}        # Delete user (admin)
```

### 2. Database Migration Completion

**Files to Modify:**
- `alembic/versions/` - Create initial migration
- `src/purple_team_gpt/db/database.py` - Ensure proper initialization

**Migration Steps:**
1. Verify all models in `db/models.py` are correct
2. Generate initial migration with `alembic revision --autogenerate`
3. Add seed data for default roles and permissions
4. Wire orchestrator to use database persistence

### 3. LLM Provider Integration

**Files to Modify:**
- `src/purple_team_gpt/core/llm/engine.py` - Add Gemini
- `src/purple_team_gpt/config.py` - Add Gemini configuration

**Provider Configuration:**

```python
# config.py additions
class LLMSettings(BaseSettings):
    # Existing providers
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    
    # NEW: Gemini
    gemini_api_key: Optional[str] = None
    
    # NEW: OpenAI-compatible auto-detection
    openai_compatible_url: Optional[str] = None
    openai_compatible_key: Optional[str] = None
```

### 4. Token Budget Management

**Files to Create:**
- `src/purple_team_gpt/core/llm/budget.py`

**Implementation:**

```python
class TokenBudget:
    """Prevent context window overflow and manage token costs."""
    
    PROVIDER_LIMITS = {
        "openai": {"gpt-4o": 128000, "gpt-4o-mini": 128000},
        "anthropic": {"claude-sonnet-4-20250514": 200000},
        "gemini": {"gemini-2.0-flash": 1000000},
    }
    
    def count_tokens(self, messages: List[Dict]) -> int:
        """Estimate token count for messages."""
        
    def check_budget(self, messages: List[Dict]) -> bool:
        """Return True if within budget."""
        
    def truncate_messages(self, messages: List[Dict]) -> List[Dict]:
        """Remove oldest messages to fit budget."""
```

### 5. Response Caching Layer

**Files to Create:**
- `src/purple_team_gpt/core/llm/cache.py`

**Implementation:**

```python
class SemanticCache:
    """Cache LLM responses by semantic similarity."""
    
    def __init__(self, similarity_threshold: float = 0.95, ttl: int = 3600):
        self.threshold = similarity_threshold
        self.ttl = ttl
        
    async def get_cached(self, prompt: str, embedding: List[float]) -> Optional[str]:
        """Return cached response if similar prompt exists."""
        
    async def cache_response(self, prompt: str, embedding: List[float], response: str):
        """Store response with embedding for similarity matching."""
```

### 6. Agent Memory Persistence

**Files to Create:**
- `src/purple_team_gpt/agents/memory.py`

**Implementation:**

```python
class AgentMemory:
    """Persist agent state and learnings across sessions."""
    
    async def save_session(self, session_id: str, state: Dict):
        """Save agent state at end of session."""
        
    async def load_session(self, session_id: str) -> Optional[Dict]:
        """Load previous session state."""
        
    async def save_learning(self, learning: AgentLearning):
        """Store a learned pattern for future use."""
```

### 7. Tool Output Parsers

**Files to Create:**
- `src/purple_team_gpt/tools/parsers.py`

**Implementation:**

```python
class NmapParser(ToolOutputParser):
    """Parse nmap scan results."""
    def parse(self, output: str) -> NmapScan:
        """Extract ports, services, OS, vulnerabilities."""

class NiktoParser(ToolOutputParser):
    """Parse nikto web scan results."""
    def parse(self, output: str) -> List[NiktoFinding]:
        """Extract web vulnerabilities."""
```

### 8. Frontend Error Boundaries

**Files to Create:**
- `src/frontend/src/components/ErrorBoundary.tsx`

---

## Implementation Phases

### Phase 1: Core Fixes (Days 1-7)

**Priority: P0 - Blocking everything**

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | User authentication | Users can register, login, get JWT |
| 2-3 | Database migration | Schema migrated, data seeded |
| 3-4 | Wire orchestrator to DB | Sessions persist across restarts |
| 4-5 | Frontend error boundaries | Graceful error handling in UI |
| 5-6 | API error handling | Consistent error responses |
| 6-7 | Integration testing | Core flow works end-to-end |

### Phase 2: LLM Provider Integration (Days 8-14)

**Priority: P1 - Enhanced functionality**

| Day | Task | Deliverable |
|-----|------|-------------|
| 8 | Gemini integration | Gemini API working |
| 9 | Provider health monitoring | Health checks for all providers |
| 10 | Token budget management | No context overflow errors |
| 11-12 | Response caching | Cache hit rate > 30% |
| 13 | Provider health dashboard | UI shows provider status |
| 14 | Multi-provider testing | Failover works correctly |

### Phase 3: Quality & Testing (Days 15-21)

**Priority: P1 - Production reliability**

| Day | Task | Deliverable |
|-----|------|-------------|
| 15-17 | Test coverage to 80% | 500+ tests passing |
| 18-19 | Tool output parsers | Structured tool data |
| 20 | Agent memory persistence | Learnings persist across sessions |
| 21 | Embedding cache | Faster RAG queries |

### Phase 4: Polish & Documentation (Days 22-28)

**Priority: P2 - Usability**

| Day | Task | Deliverable |
|-----|------|-------------|
| 22-23 | API documentation | Complete API docs |
| 24 | Setup guide | Quickstart guide |
| 25 | Configuration validation | Clear startup errors |
| 26-27 | E2E testing | Full user flows tested |
| 28 | Final integration | Everything works together |

---

## Success Metrics

### Functionality Metrics

| Metric | Target |
|--------|--------|
| User registration success rate | > 99% |
| Session persistence rate | 100% |
| LLM request success rate | > 95% |
| Provider failover time | < 2s |
| Cache hit rate | > 30% |

### Quality Metrics

| Metric | Target |
|--------|--------|
| Test coverage | ≥ 80% |
| Test pass rate | 100% |
| Documentation coverage | 100% API |

### Performance Metrics

| Metric | Target |
|--------|--------|
| API response time (p95) | < 200ms |
| WebSocket latency | < 100ms |
| RAG query time | < 200ms |
| Session startup time | < 5s |

---

## File Change Summary

### New Files to Create

| File | Purpose |
|------|---------|
| `backend/routers/users.py` | User management API |
| `backend/routers/auth.py` | Authentication API |
| `core/llm/budget.py` | Token management |
| `core/llm/cache.py` | Response caching |
| `agents/memory.py` | Agent persistence |
| `tools/parsers.py` | Tool output parsing |
| `frontend/src/components/ErrorBoundary.tsx` | Error handling |
| Multiple test files | Test coverage |

### Files to Modify

| File | Changes |
|------|---------|
| `core/llm/engine.py` | Add Gemini, budget, cache |
| `config.py` | Add Gemini config, validation |
| `core/orchestrator.py` | Wire to database, add memory |
| `backend/main.py` | Include new routers |
| `alembic/` | Create migrations |

---

## Conclusion

This design provides a comprehensive roadmap to transform Purple Team GPT into a production-ready system. The phased approach ensures early delivery of core functionality while building toward a complete, reliable, and well-tested application.
