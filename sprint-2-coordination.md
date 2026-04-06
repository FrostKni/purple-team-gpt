# Sprint 2 Coordination Document
## Purple Team GPT - Production Readiness & Quality

**Sprint Duration:** April 15 - April 28, 2026 (2 weeks)  
**Last Updated:** April 1, 2026

---

## 1. Executive Summary

Sprint 2 focuses on transforming Purple Team GPT from a development prototype to a production-ready system. The primary objectives are:

1. **Database Persistence** - Replace in-memory session storage with PostgreSQL
2. **Production Security** - Implement HTTPS and secrets management
3. **Error Boundaries** - Frontend resilience with React error boundaries
4. **Test Coverage** - Achieve 80% coverage across backend and frontend
5. **Agent Tool Safety** - Enhanced validation and execution controls

---

## 2. Team Assignments

| Agent ID | Name | Role | Tasks | Hours |
|----------|------|------|-------|-------|
| dev-1 | Alex Chen | Senior Backend Engineer | DB-001, DB-002, DOC-003 | 34h |
| dev-2 | Jordan Riley | Senior Backend Engineer | DB-003, SEC-007, SEC-008, DOC-004 | 40h |
| dev-3 | Sam Martinez | Frontend Engineer | FE-001, FE-002 | 14h |
| dev-4 | Taylor Kim | Full Stack Engineer | TEST-003, AI-001, AI-002 | 34h |
| dev-5 | Morgan Davis | QA Engineer | TEST-004, TEST-005 | 26h |

**Total Estimated Hours:** 148h

---

## 3. Task Dependency Graph

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    SPRINT 2 DEPENDENCIES                 │
                    └─────────────────────────────────────────────────────────┘

TIER 1 - NO DEPENDENCIES (Can start Day 1)
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   DB-001    │  │   SEC-007   │  │   FE-001    │  │  TEST-003   │  │   AI-001    │
│  Database   │  │   HTTPS/    │  │   Error     │  │  Backend    │  │   Tool      │
│   Schema    │  │    TLS      │  │ Boundaries  │  │   Tests     │  │ Validation  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────┘  └──────┬──────┘
       │                │                │                                │
       │                │                │                                │
TIER 2 - DEPENDS ON TIER 1                      │                       │
       │                │                │                                │
       ▼                ▼                ▼                                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 ┌─────────────┐
│   DB-002    │  │   SEC-008   │  │   FE-002    │                 │   AI-002    │
│  Session    │  │  Secrets    │  │ API Error   │                 │  Tool       │
│ Persistence │  │ Management  │  │  Handling   │                 │  Timeouts   │
└──────┬──────┘  └──────┬──────┘  └─────────────┘                 └─────────────┘
       │                │                │
       │                │                │
       │                │                │
       │                ▼                │
       │         ┌─────────────┐         │
       │         │   DOC-004   │         │
       │         │ Deployment  │         │
       │         │    Docs     │         │
       │         └─────────────┘         │
       │                                 │
TIER 3 - DEPENDS ON TIER 2                │
       │                                 │
       ▼                                 ▼
┌─────────────┐                   ┌─────────────┐
│   DB-003    │                   │  TEST-004   │
│   Redis     │                   │  Frontend   │
│ Integration │                   │   Tests     │
└─────────────┘                   └─────────────┘
       │
       │
TIER 4 - DEPENDS ON TIER 2 & 3
       │
       ▼
┌─────────────┐
│  TEST-005   │
│    E2E      │
│   Tests     │
└─────────────┘

INDEPENDENT TASKS (Any time):
┌─────────────┐
│   DOC-003   │
│    API      │
│    Docs     │
└─────────────┘
```

### Critical Path Analysis

```
CRITICAL PATH (Longest duration):
DB-001 (12h) → DB-002 (16h) → TEST-005 (12h) = 40 hours minimum

This path determines the minimum sprint duration for database work.
```

---

## 4. Integration Checkpoints

### Checkpoint 1: Day 3 (April 17)
**Database Foundation Complete**
- [ ] DB-001: Schema designed, Alembic configured, models created
- [ ] SEC-007: HTTPS configuration drafted, cert scripts ready
- [ ] FE-001: Error boundaries implemented
- [ ] AI-001: Tool validation framework in place

**Checkpoint Owner:** Alex Chen (dev-1)

### Checkpoint 2: Day 5 (April 21)
**Core Integration Ready**
- [ ] DB-002: Session persistence layer complete
- [ ] SEC-008: Secrets management implemented
- [ ] FE-002: API error handling integrated
- [ ] AI-002: Tool timeout/safety features complete

**Checkpoint Owner:** Jordan Riley (dev-2)

### Checkpoint 3: Day 7 (April 23)
**Full Stack Integration**
- [ ] DB-003: Redis integration complete
- [ ] TEST-003: Backend coverage >= 80%
- [ ] TEST-004: Frontend coverage >= 80%
- [ ] DOC-003: API documentation complete

**Checkpoint Owner:** Taylor Kim (dev-4)

### Checkpoint 4: Day 9 (April 25)
**Production Readiness**
- [ ] TEST-005: E2E tests passing
- [ ] DOC-004: Deployment documentation complete
- [ ] All P0 tasks verified complete
- [ ] Integration tests passing

**Checkpoint Owner:** Morgan Davis (dev-5)

---

## 5. Database Migration Plan

### 5.1 Current State (In-Memory Storage)

**Location:** `src/purple_team_gpt/core/orchestrator.py`

```python
# Current in-memory storage
self.sessions: Dict[str, Session] = {}
self.red_agents: Dict[str, RedAgent] = {}
self.blue_agents: Dict[str, BlueAgent] = {}
self._event_queues: Dict[str, asyncio.Queue] = {}
```

**Issues:**
- Sessions lost on application restart
- No transactional guarantees
- Cannot scale horizontally
- No audit trail

### 5.2 Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Session Router  │  │ Orchestrator    │  │  Agent Services │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
└───────────┼────────────────────┼────────────────────┼──────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REPOSITORY LAYER                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │SessionRepository│  │ FindingRepo     │  │  EventRepo      │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
└───────────┼────────────────────┼────────────────────┼──────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL                            │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │   │
│  │  │  sessions   │ │  findings   │ │  session_events     │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      Redis                               │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │   │
│  │  │   Cache     │ │ Rate Limits │ │  Session State      │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 PostgreSQL Schema Design

```sql
-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target VARCHAR(500) NOT NULL,
    scope TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    initialization_error TEXT,
    
    -- Indexes for common queries
    INDEX idx_sessions_status (status),
    INDEX idx_sessions_created_at (created_at),
    INDEX idx_sessions_last_activity (last_activity_at)
);

-- Findings table
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_type VARCHAR(10) NOT NULL,  -- 'red' or 'blue'
    title VARCHAR(500) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    evidence TEXT,
    recommendation TEXT,
    tool VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_findings_session (session_id),
    INDEX idx_findings_severity (severity),
    INDEX idx_findings_agent (agent_type)
);

-- Session events table
CREATE TABLE session_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    data JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_events_session (session_id),
    INDEX idx_events_timestamp (timestamp)
);

-- Agent state snapshots (for pause/resume)
CREATE TABLE agent_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_type VARCHAR(10) NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(session_id, agent_type)
);
```

### 5.4 Migration Phases

#### Phase 1: Schema Setup (Day 1-2)
**Owner:** dev-1 (Alex Chen)

```bash
# Tasks:
1. Install dependencies: psycopg2-binary, alembic, sqlmodel
2. Create alembic configuration
3. Create initial migration
4. Set up database connection pooling
```

**Files to Create:**
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/001_initial_schema.py`
- `src/purple_team_gpt/models/database.py`
- `src/purple_team_gpt/models/session.py`
- `src/purple_team_gpt/models/finding.py`

#### Phase 2: Repository Layer (Day 3-4)
**Owner:** dev-1 (Alex Chen)

```python
# src/purple_team_gpt/services/session_repository.py

class SessionRepository:
    """Repository for session persistence."""
    
    async def create(self, session: Session) -> Session:
        """Create a new session in database."""
        
    async def get(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        
    async def update(self, session: Session) -> Session:
        """Update session state."""
        
    async def delete(self, session_id: str) -> bool:
        """Delete session and related data."""
        
    async def list(self, status: Optional[str] = None) -> List[Session]:
        """List sessions with optional filter."""
        
    async def cleanup_expired(self, timeout_minutes: int) -> int:
        """Clean up expired sessions."""
```

#### Phase 3: Orchestrator Integration (Day 5-6)
**Owner:** dev-1 (Alex Chen)

```python
# Update orchestrator to use repository

class PurpleOrchestrator:
    def __init__(
        self,
        engine: LLMEngine,
        vector_store: VectorStore,
        session_repository: SessionRepository,  # NEW
        cache_service: Optional[CacheService] = None,  # NEW
        ...
    ):
        self.session_repository = session_repository
        self.cache = cache_service
        
    async def create_session(self, target: str, scope: str = "", ...) -> Session:
        """Create session with persistence."""
        session = Session(target=target, scope=scope)
        await self.session_repository.create(session)
        # ... rest of initialization
```

#### Phase 4: Redis Integration (Day 7-8)
**Owner:** dev-2 (Jordan Riley)

```python
# src/purple_team_gpt/services/cache.py

class CacheService:
    """Redis-based caching service."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set cached value with TTL."""
        
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        
    async def invalidate_session(self, session_id: str) -> None:
        """Invalidate all cache keys for a session."""
```

### 5.5 Rollback Procedures

#### Database Migration Rollback

```bash
# Rollback to previous migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

#### Application Rollback

```yaml
# docker-compose rollback procedure
# 1. Tag current deployment
docker tag purple-team-backend:latest purple-team-backend:backup

# 2. Deploy previous version
docker-compose down backend
docker-compose up -d backend:previous-version

# 3. Verify health
curl http://localhost:8000/health
```

#### Data Recovery

```sql
-- Backup before migration
pg_dump purple_team_gpt > backup_pre_migration.sql

-- Restore from backup
psql purple_team_gpt < backup_pre_migration.sql

-- Point-in-time recovery (if WAL archiving enabled)
pg_restore --target-time "2026-04-20 10:00:00" backup_file
```

---

## 6. Integration Test Plan

### 6.1 Test Categories

| Category | Owner | Coverage Target | Dependencies |
|----------|-------|-----------------|--------------|
| Unit Tests - Backend | dev-4 | 80% | None |
| Unit Tests - Frontend | dev-5 | 80% | FE-001 |
| Integration Tests | dev-4 | Critical paths | DB-002 |
| E2E Tests | dev-5 | User flows | DB-002, FE-001 |

### 6.2 Backend Test Structure

```
tests/
├── unit/
│   ├── models/
│   │   ├── test_session_model.py
│   │   ├── test_finding_model.py
│   │   └── test_user_model.py
│   ├── services/
│   │   ├── test_session_repository.py
│   │   ├── test_cache_service.py
│   │   └── test_tool_manager.py
│   ├── agents/
│   │   ├── test_red_agent.py
│   │   ├── test_blue_agent.py
│   │   └── test_agent_base.py
│   └── orchestrator/
│       └── test_orchestrator.py
├── integration/
│   ├── test_session_persistence.py
│   ├── test_redis_integration.py
│   └── test_database_migrations.py
└── conftest.py
```

### 6.3 Critical Test Cases

#### Session Persistence Tests

```python
# tests/integration/test_session_persistence.py

class TestSessionPersistence:
    """Integration tests for session persistence."""
    
    @pytest.mark.asyncio
    async def test_session_persists_across_restart(self, session_repo):
        """Session should survive application restart."""
        session = await session_repo.create(Session(target="192.168.1.1"))
        
        # Simulate restart
        await session_repo.close()
        await session_repo.connect()
        
        retrieved = await session_repo.get(session.id)
        assert retrieved is not None
        assert retrieved.target == "192.168.1.1"
    
    @pytest.mark.asyncio
    async def test_finding_cascade_delete(self, session_repo, finding_repo):
        """Deleting session should delete all findings."""
        session = await session_repo.create(Session(target="test"))
        finding = await finding_repo.create(Finding(session_id=session.id))
        
        await session_repo.delete(session.id)
        
        assert await finding_repo.get(finding.id) is None
    
    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, session_repo):
        """Handle concurrent session updates safely."""
        session = await session_repo.create(Session(target="test"))
        
        # Simulate concurrent updates
        tasks = [
            session_repo.update(session.id, {"status": "running"})
            for _ in range(10)
        ]
        await asyncio.gather(*tasks)
        
        final = await session_repo.get(session.id)
        assert final.status == "running"
```

#### Redis Integration Tests

```python
# tests/integration/test_redis_integration.py

class TestRedisIntegration:
    """Integration tests for Redis caching."""
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_session_update(self, cache, session_repo):
        """Cache should be invalidated when session is updated."""
        session = await session_repo.create(Session(target="test"))
        await cache.set(f"session:{session.id}", session.to_dict())
        
        await session_repo.update(session.id, {"status": "running"})
        
        cached = await cache.get(f"session:{session.id}")
        assert cached is None  # Should be invalidated
    
    @pytest.mark.asyncio
    async def test_rate_limiting_with_redis(self, rate_limiter):
        """Rate limiting should work with Redis backend."""
        client_id = "test-client"
        
        for i in range(100):
            allowed = await rate_limiter.check(client_id)
            assert allowed is True
        
        # 101st request should be blocked
        allowed = await rate_limiter.check(client_id)
        assert allowed is False
```

### 6.4 E2E Test Scenarios (Playwright)

```typescript
// e2e/tests/session-flow.spec.ts

test.describe('Session Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[name="username"]', 'test_user');
    await page.fill('[name="password"]', 'test_pass');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
  });

  test('should create and run a session', async ({ page }) => {
    // Create session
    await page.click('text=New Session');
    await page.fill('[name="target"]', '192.168.1.1');
    await page.fill('[name="scope"]', 'Penetration test authorized');
    await page.click('button:has-text("Create")');
    
    // Verify session created
    await expect(page.locator('.session-status')).toHaveText('pending');
    
    // Start session
    await page.click('button:has-text("Start")');
    await expect(page.locator('.session-status')).toHaveText('running', { timeout: 10000 });
    
    // Wait for events
    await expect(page.locator('.event-item')).toHaveCount(1, { timeout: 30000 });
  });

  test('should handle session pause/resume', async ({ page }) => {
    // ... pause/resume test
  });

  test('should display error boundary for API errors', async ({ page, context }) => {
    // Simulate API failure
    await context.route('**/api/v1/sessions', route => route.abort());
    
    await page.goto('/');
    
    // Should show error boundary
    await expect(page.locator('.error-boundary')).toBeVisible();
    await expect(page.locator('button:has-text("Retry")')).toBeVisible();
  });
});
```

### 6.5 Test Execution Order

```
Day 1-3: Unit Tests (Parallel Development)
├── Backend models tests
├── Frontend component tests
└── Error boundary tests

Day 4-5: Integration Tests (After DB-002)
├── Session persistence tests
├── Redis integration tests
└── Rate limiting tests

Day 6-7: E2E Tests (After FE-001, DB-002)
├── Login flow
├── Session creation flow
├── Session control flow
└── Error handling flow

Day 8-9: Full Regression
├── All tests in CI pipeline
├── Coverage report generation
└── Performance benchmarks
```

---

## 7. Risk Mitigation

### Risk Matrix

| Risk ID | Description | Impact | Probability | Mitigation |
|---------|-------------|--------|-------------|------------|
| RISK-001 | Database migration data loss | High | Medium | Migration scripts with rollback, staging tests |
| RISK-002 | Redis single point of failure | Medium | Medium | Fallback to in-memory, health checks |
| RISK-003 | Test coverage takes longer | Medium | High | Prioritize critical paths, coverage reports |
| RISK-004 | HTTPS setup issues | High | Low | Isolated testing, cert documentation |
| RISK-005 | E2E test flakiness | Low | Medium | Deterministic data, retry logic |

### Contingency Plans

**If Database Migration Fails:**
1. Execute rollback procedure
2. Revert to in-memory storage
3. Investigate and fix migration script
4. Re-attempt with fresh backup

**If Test Coverage < 80%:**
1. Focus on critical paths first
2. Accept lower coverage for non-critical modules
3. Document technical debt for Sprint 3

---

## 8. Communication Plan

### Daily Standups
- **Time:** 9:00 AM (Team timezone)
- **Duration:** 15 minutes
- **Format:** What I did, What I'm doing, Blockers

### Integration Sync
- **Frequency:** Every checkpoint (Days 3, 5, 7, 9)
- **Attendees:** All team members
- **Focus:** Cross-team dependencies, integration issues

### Slack Channels
- `#sprint-2-db` - Database migration discussions
- `#sprint-2-frontend` - Frontend error boundaries
- `#sprint-2-testing` - Test coverage coordination

---

## 9. Definition of Done

Each task must meet ALL criteria before marking complete:

- [ ] All acceptance criteria met
- [ ] Code reviewed and approved (2 reviewers minimum)
- [ ] Unit tests passing with >80% coverage for new code
- [ ] Integration tests passing
- [ ] Security scan clean (no new vulnerabilities)
- [ ] Documentation updated
- [ ] Deployed to staging environment
- [ ] QA sign-off received
- [ ] Performance benchmarks met (where applicable)

---

## 10. Success Criteria

Sprint 2 is successful when:

1. **All P0 tasks completed** (DB-001, DB-002, SEC-007, SEC-008)
2. **Test coverage >= 80%** (backend + frontend)
3. **All sessions persist across restarts**
4. **HTTPS working in production config**
5. **E2E tests passing for critical flows**
6. **No new security vulnerabilities introduced**

---

## Appendix A: File Locations

### New Files (To Create)

```
src/purple_team_gpt/
├── models/
│   ├── __init__.py
│   ├── database.py          # DB connection, session management
│   ├── session.py           # Session SQLAlchemy model
│   ├── finding.py           # Finding SQLAlchemy model
│   └── user.py              # User SQLAlchemy model
├── services/
│   ├── session_repository.py
│   ├── finding_repository.py
│   └── cache.py             # Redis cache service
├── config/
│   └── secrets.py           # Secrets management

alembic/
├── env.py
├── versions/
│   └── 001_initial_schema.py
└── alembic.ini

src/frontend/src/components/
├── ErrorBoundary.tsx
└── ErrorMessage.tsx

e2e/
├── tests/
│   ├── login.spec.ts
│   ├── session-flow.spec.ts
│   └── error-handling.spec.ts
└── playwright.config.ts

deploy/
├── vault/
│   └── config.hcl
└── production/
    └── docker-compose.prod.yml
```

### Files to Modify

```
src/purple_team_gpt/
├── core/orchestrator.py      # Add repository injection
├── backend/routers/sessions.py  # Use repository
├── backend/main.py           # Add DB lifespan
├── backend/security.py       # Redis rate limiter
└── config.py                 # Add DB settings

docker-compose.yml            # Add PostgreSQL service
src/frontend/src/App.tsx      # Add error boundaries
```

---

**Document Version:** 1.0  
**Author:** Sprint Lead (Orchestrator Agent)  
**Approved By:** [Pending Review]