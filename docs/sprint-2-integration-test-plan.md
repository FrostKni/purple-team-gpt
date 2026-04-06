# Sprint 2 Integration Test Plan
## Purple Team GPT - Production Readiness Testing

**Version:** 1.0  
**Created:** April 1, 2026  
**Owner:** Morgan Davis (dev-5) + Taylor Kim (dev-4)

---

## 1. Test Strategy Overview

### 1.1 Testing Pyramid

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E╲         ← TEST-005 (Playwright)
                 ╱──────╲           12h, dev-5
                ╱        ╲
               ╱Integration╲     ← Integration Tests
              ╱─────────────╲        Day 6-7
             ╱               ╲
            ╱   Unit Tests    ╲   ← TEST-003, TEST-004
           ╱───────────────────╲      80% coverage target
          ╱                     ╲
         ╱_______________________╲
```

### 1.2 Test Environment Requirements

| Environment | Purpose | Configuration |
|-------------|---------|---------------|
| Development | Local testing | SQLite, in-memory Redis mock |
| CI Pipeline | Automated testing | PostgreSQL test DB, Redis container |
| Staging | Pre-production | Full Docker Compose stack |
| Production | Live testing | Read-only smoke tests |

---

## 2. Unit Test Plan

### 2.1 Backend Unit Tests (TEST-003)

**Owner:** Taylor Kim (dev-4)  
**Target Coverage:** 80%  
**Duration:** 16 hours

#### Test File Structure

```
tests/
├── unit/
│   ├── models/
│   │   ├── test_session_model.py
│   │   ├── test_finding_model.py
│   │   └── test_user_model.py
│   ├── services/
│   │   ├── test_session_repository.py
│   │   ├── test_finding_repository.py
│   │   ├── test_cache_service.py
│   │   └── test_tool_manager.py
│   ├── agents/
│   │   ├── test_red_agent.py
│   │   ├── test_blue_agent.py
│   │   └── test_base_agent.py
│   ├── core/
│   │   ├── test_orchestrator.py
│   │   ├── test_llm_engine.py
│   │   └── test_vector_store.py
│   ├── security/
│   │   ├── test_auth.py
│   │   ├── test_rate_limiter.py
│   │   └── test_input_validation.py
│   └── backend/
│       ├── test_sessions_router.py
│       ├── test_websocket_router.py
│       └── test_feedback_router.py
└── conftest.py
```

#### Critical Unit Test Cases

**Session Model Tests**

```python
# tests/unit/models/test_session_model.py

class TestSessionModel:
    """Unit tests for Session model."""
    
    def test_session_creation_with_defaults(self):
        """Session should have default values."""
        session = Session(target="192.168.1.1")
        assert session.status == SessionStatus.PENDING
        assert session.created_at is not None
        assert session.red_findings == []
        assert session.blue_findings == []
    
    def test_session_status_transitions(self):
        """Session status should transition correctly."""
        session = Session(target="test")
        
        # Valid transitions
        session.status = SessionStatus.INITIALIZING
        session.status = SessionStatus.RUNNING
        session.status = SessionStatus.PAUSED
        session.status = SessionStatus.RUNNING  # Resume
        session.status = SessionStatus.COMPLETED
        
        assert session.status == SessionStatus.COMPLETED
    
    def test_session_to_dict_serialization(self):
        """Session should serialize to dict correctly."""
        session = Session(
            target="test",
            scope="authorized test",
            status=SessionStatus.RUNNING
        )
        
        data = session.to_dict()
        
        assert data["target"] == "test"
        assert data["status"] == "running"
        assert "created_at" in data
        assert "id" in data
    
    def test_session_is_idle_detection(self):
        """Session should detect idle state correctly."""
        session = Session(target="test")
        
        # New session is not idle
        assert not session.is_idle(timeout_minutes=60)
        
        # Simulate old session
        session.last_activity_at = datetime.utcnow() - timedelta(minutes=61)
        assert session.is_idle(timeout_minutes=60)
        
        # Completed sessions are always idle
        session.status = SessionStatus.COMPLETED
        assert session.is_idle(timeout_minutes=0)
```

**Session Repository Tests**

```python
# tests/unit/services/test_session_repository.py

class TestSessionRepository:
    """Unit tests for SessionRepository."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def repository(self, mock_db_session):
        """Create repository with mock session."""
        return SessionRepository(db_session=mock_db_session)
    
    @pytest.mark.asyncio
    async def test_create_session(self, repository, mock_db_session):
        """Should create session in database."""
        session = Session(target="192.168.1.1", scope="test")
        
        result = await repository.create(session)
        
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        assert result == session
    
    @pytest.mark.asyncio
    async def test_get_session_not_found(self, repository, mock_db_session):
        """Should return None if session not found."""
        mock_db_session.get.return_value = None
        
        result = await repository.get("non-existent-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_session(self, repository, mock_db_session):
        """Should update session in database."""
        session = Session(id="test-id", target="test", status=SessionStatus.RUNNING)
        mock_db_session.get.return_value = session
        
        result = await repository.update("test-id", {"status": "completed"})
        
        mock_db_session.commit.assert_called_once()
        assert session.status == SessionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_delete_session_cascades(self, repository, mock_db_session):
        """Should delete session and cascade to findings."""
        session = Session(id="test-id", target="test")
        mock_db_session.get.return_value = session
        
        result = await repository.delete("test-id")
        
        mock_db_session.delete.assert_called_once_with(session)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_list_sessions_with_filter(self, repository, mock_db_session):
        """Should filter sessions by status."""
        mock_db_session.exec.return_value = [
            Session(target="test1", status=SessionStatus.RUNNING),
            Session(target="test2", status=SessionStatus.RUNNING),
        ]
        
        results = await repository.list(status=SessionStatus.RUNNING)
        
        assert len(results) == 2
        assert all(s.status == SessionStatus.RUNNING for s in results)
```

**Cache Service Tests**

```python
# tests/unit/services/test_cache_service.py

class TestCacheService:
    """Unit tests for Redis cache service."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)
        return redis
    
    @pytest.fixture
    def cache_service(self, mock_redis):
        """Create cache service with mock Redis."""
        return CacheService(redis_client=mock_redis)
    
    @pytest.mark.asyncio
    async def test_cache_get_miss(self, cache_service, mock_redis):
        """Should return None on cache miss."""
        mock_redis.get.return_value = None
        
        result = await cache_service.get("missing-key")
        
        assert result is None
        mock_redis.get.assert_called_once_with("missing-key")
    
    @pytest.mark.asyncio
    async def test_cache_get_hit(self, cache_service, mock_redis):
        """Should return cached value on hit."""
        mock_redis.get.return_value = json.dumps({"target": "test"})
        
        result = await cache_service.get("session:123")
        
        assert result == {"target": "test"}
    
    @pytest.mark.asyncio
    async def test_cache_set_with_ttl(self, cache_service, mock_redis):
        """Should set value with TTL."""
        await cache_service.set("session:123", {"target": "test"}, ttl=3600)
        
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "session:123"
        assert call_args[1].get("ex") == 3600
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_service, mock_redis):
        """Should delete cached value."""
        mock_redis.delete.return_value = 1
        
        result = await cache_service.delete("session:123")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("session:123")
    
    @pytest.mark.asyncio
    async def test_cache_invalidate_pattern(self, cache_service, mock_redis):
        """Should invalidate all keys matching pattern."""
        mock_redis.keys.return_value = [b"session:123:events", b"session:123:state"]
        
        await cache_service.invalidate_pattern("session:123:*")
        
        assert mock_redis.delete.call_count == 2
```

### 2.2 Frontend Unit Tests (TEST-004)

**Owner:** Morgan Davis (dev-5)  
**Target Coverage:** 80%  
**Duration:** 14 hours

#### Test File Structure

```
src/frontend/src/
├── __tests__/
│   ├── components/
│   │   ├── ErrorBoundary.test.tsx
│   │   ├── ErrorMessage.test.tsx
│   │   ├── SessionCard.test.tsx
│   │   └── SessionList.test.tsx
│   ├── hooks/
│   │   ├── useApi.test.ts
│   │   ├── useWebSocket.test.ts
│   │   └── useSession.test.ts
│   ├── lib/
│   │   └── api.test.ts
│   └── App.test.tsx
└── jest.setup.ts
```

#### Critical Frontend Test Cases

**Error Boundary Tests**

```typescript
// src/frontend/src/__tests__/components/ErrorBoundary.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '../../components/ErrorBoundary';

describe('ErrorBoundary', () => {
  const ThrowError = () => {
    throw new Error('Test error');
  };

  beforeEach(() => {
    // Suppress console.error for cleaner test output
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('should render children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('should display error UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('should reset error state on retry click', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    // Click retry button
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));

    // Rerender with non-throwing component
    rerender(
      <ErrorBoundary>
        <div>Fixed content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Fixed content')).toBeInTheDocument();
  });

  it('should log error to monitoring service', () => {
    const logError = jest.fn();
    
    render(
      <ErrorBoundary onError={logError}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(logError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.any(Object)
    );
  });
});
```

**API Hook Tests**

```typescript
// src/frontend/src/__tests__/hooks/useApi.test.ts

import { renderHook, waitFor } from '@testing-library/react';
import { useApi } from '../../hooks/useApi';

describe('useApi', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('should fetch data successfully', async () => {
    const mockData = { sessions: [] };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const { result } = renderHook(() => useApi('/api/v1/sessions'));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  it('should handle fetch errors with retry', async () => {
    (global.fetch as jest.Mock)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

    const { result } = renderHook(() => 
      useApi('/api/v1/sessions', { retries: 2, retryDelay: 100 })
    );

    await waitFor(() => expect(result.current.loading).toBe(false), {
      timeout: 2000,
    });

    expect(result.current.data).toEqual({ success: true });
    expect(global.fetch).toHaveBeenCalledTimes(3);
  });

  it('should fail after max retries', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(
      new Error('Network error')
    );

    const { result } = renderHook(() => 
      useApi('/api/v1/sessions', { retries: 2, retryDelay: 100 })
    );

    await waitFor(() => expect(result.current.loading).toBe(false), {
      timeout: 2000,
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.data).toBeNull();
    expect(global.fetch).toHaveBeenCalledTimes(3);
  });

  it('should handle timeout correctly', async () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 2000))
    );

    const { result } = renderHook(() => 
      useApi('/api/v1/sessions', { timeout: 100 })
    );

    await waitFor(() => expect(result.current.loading).toBe(false), {
      timeout: 2000,
    });

    expect(result.current.error?.message).toContain('timeout');
  });
});
```

---

## 3. Integration Test Plan

### 3.1 Test Environment Setup

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  test-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: purple_team_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data

  test-redis:
    image: redis:7.2-alpine
    ports:
      - "6380:6379"

  test-runner:
    build:
      context: .
      dockerfile: docker/Dockerfile.test
    depends_on:
      - test-db
      - test-redis
    environment:
      DATABASE_URL: postgresql://test:test@test-db:5432/purple_team_test
      REDIS_URL: redis://test-redis:6379/1
    volumes:
      - ./tests:/app/tests
      - ./coverage:/app/coverage
```

### 3.2 Database Integration Tests

```python
# tests/integration/test_session_persistence.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from purple_team_gpt.models.database import Base
from purple_team_gpt.services.session_repository import SessionRepository
from purple_team_gpt.core.orchestrator import Session, SessionStatus


@pytest.fixture
def db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def repository(db_session):
    """Create session repository."""
    return SessionRepository(db_session)


class TestSessionPersistenceIntegration:
    """Integration tests for session persistence."""

    @pytest.mark.asyncio
    async def test_session_full_lifecycle(self, repository):
        """Test complete session lifecycle."""
        # Create
        session = Session(target="192.168.1.1", scope="Authorized test")
        created = await repository.create(session)
        assert created.id is not None
        
        # Read
        retrieved = await repository.get(created.id)
        assert retrieved.target == "192.168.1.1"
        
        # Update
        retrieved.status = SessionStatus.RUNNING
        updated = await repository.update(retrieved)
        assert updated.status == SessionStatus.RUNNING
        
        # Delete
        deleted = await repository.delete(created.id)
        assert deleted is True
        
        # Verify deletion
        assert await repository.get(created.id) is None

    @pytest.mark.asyncio
    async def test_session_with_findings(self, repository, finding_repository):
        """Test session with associated findings."""
        # Create session
        session = Session(target="test")
        created_session = await repository.create(session)
        
        # Add findings
        from purple_team_gpt.models.finding import Finding
        finding1 = Finding(
            session_id=created_session.id,
            agent_type="red",
            title="Open port 22",
            severity="medium"
        )
        finding2 = Finding(
            session_id=created_session.id,
            agent_type="blue",
            title="SSH brute force detected",
            severity="high"
        )
        
        await finding_repository.create(finding1)
        await finding_repository.create(finding2)
        
        # Retrieve session with findings
        session_with_findings = await repository.get_with_findings(created_session.id)
        
        assert len(session_with_findings.red_findings) == 1
        assert len(session_with_findings.blue_findings) == 1
        assert session_with_findings.blue_findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_concurrent_session_updates(self, repository):
        """Test concurrent updates are handled safely."""
        import asyncio
        
        session = Session(target="test")
        created = await repository.create(session)
        
        # Simulate concurrent updates
        async def update_status(new_status):
            return await repository.update_status(created.id, new_status)
        
        results = await asyncio.gather(
            update_status(SessionStatus.RUNNING),
            update_status(SessionStatus.PAUSED),
            update_status(SessionStatus.COMPLETED),
            return_exceptions=True
        )
        
        # One should succeed, others might fail or be overwritten
        final_session = await repository.get(created.id)
        assert final_session.status in [
            SessionStatus.RUNNING,
            SessionStatus.PAUSED,
            SessionStatus.COMPLETED
        ]

    @pytest.mark.asyncio
    async def test_session_cleanup_expired(self, repository):
        """Test cleanup of expired sessions."""
        from datetime import datetime, timedelta
        
        # Create old session
        old_session = Session(target="old")
        old_session.last_activity_at = datetime.utcnow() - timedelta(hours=2)
        await repository.create(old_session)
        
        # Create recent session
        recent_session = Session(target="recent")
        await repository.create(recent_session)
        
        # Run cleanup
        cleaned_count = await repository.cleanup_expired(timeout_minutes=60)
        
        assert cleaned_count == 1
        assert await repository.get(old_session.id) is None
        assert await repository.get(recent_session.id) is not None
```

### 3.3 Redis Integration Tests

```python
# tests/integration/test_redis_integration.py

import pytest
import redis.asyncio as redis

from purple_team_gpt.services.cache import CacheService
from purple_team_gpt.backend.security import RateLimiter


@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    client = redis.from_url("redis://localhost:6380/1")
    yield client
    await client.flushdb()
    await client.close()


@pytest.fixture
async def cache_service(redis_client):
    """Create cache service with real Redis."""
    return CacheService(redis_client)


@pytest.fixture
async def rate_limiter(redis_client):
    """Create rate limiter with real Redis."""
    return RateLimiter(redis_client, requests=10, window_seconds=60)


class TestRedisCacheIntegration:
    """Integration tests for Redis caching."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_service):
        """Test basic cache operations."""
        await cache_service.set("test:key", {"value": "data"}, ttl=60)
        
        result = await cache_service.get("test:key")
        
        assert result == {"value": "data"}

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache_service):
        """Test cache key expiration."""
        import asyncio
        
        await cache_service.set("expiring:key", "data", ttl=1)
        
        # Should exist immediately
        assert await cache_service.get("expiring:key") == "data"
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Should be expired
        assert await cache_service.get("expiring:key") is None

    @pytest.mark.asyncio
    async def test_cache_invalidation_pattern(self, cache_service):
        """Test pattern-based cache invalidation."""
        # Set multiple related keys
        await cache_service.set("session:123:state", {"status": "running"})
        await cache_service.set("session:123:metrics", {"steps": 5})
        await cache_service.set("session:456:state", {"status": "pending"})
        
        # Invalidate session 123 keys
        await cache_service.invalidate_pattern("session:123:*")
        
        # Verify correct keys invalidated
        assert await cache_service.get("session:123:state") is None
        assert await cache_service.get("session:123:metrics") is None
        assert await cache_service.get("session:456:state") is not None


class TestRateLimiterIntegration:
    """Integration tests for Redis rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests(self, rate_limiter):
        """Test rate limiter allows requests within limit."""
        client_id = "test-client-1"
        
        for i in range(10):
            allowed = await rate_limiter.check(client_id)
            assert allowed is True, f"Request {i+1} should be allowed"

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excess(self, rate_limiter):
        """Test rate limiter blocks excess requests."""
        client_id = "test-client-2"
        
        # Use up limit
        for _ in range(10):
            await rate_limiter.check(client_id)
        
        # Next request should be blocked
        allowed = await rate_limiter.check(client_id)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(self, rate_limiter):
        """Test rate limit resets after window."""
        import asyncio
        
        client_id = "test-client-3"
        
        # Use up limit
        for _ in range(10):
            await rate_limiter.check(client_id)
        
        # Wait for window to reset (using short window in test)
        await asyncio.sleep(61)
        
        # Should be allowed again
        allowed = await rate_limiter.check(client_id)
        assert allowed is True
```

---

## 4. E2E Test Plan (Playwright)

### 4.1 Test Configuration

```typescript
// playwright.config.ts

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### 4.2 Critical E2E Scenarios

```typescript
// e2e/tests/session-workflow.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Session Workflow', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    // Get auth token
    const response = await request.post('/auth/token', {
      data: { username: 'test_user', password: 'test_pass' }
    });
    const data = await response.json();
    authToken = data.access_token;
  });

  test.beforeEach(async ({ page }) => {
    // Set auth cookie
    await page.context().addCookies([{
      name: 'auth_token',
      value: authToken,
      domain: 'localhost',
      path: '/',
    }]);
    
    await page.goto('/');
  });

  test('complete session lifecycle', async ({ page }) => {
    // Step 1: Create session
    await page.click('[data-testid="new-session-button"]');
    
    await page.fill('[name="target"]', '192.168.1.100');
    await page.fill('[name="scope"]', 'Authorized penetration test');
    await page.click('button[type="submit"]');
    
    // Verify session created
    await expect(page.locator('[data-testid="session-status"]')).toHaveText('pending');
    const sessionId = await page.locator('[data-testid="session-id"]').textContent();
    expect(sessionId).toBeTruthy();
    
    // Step 2: Start session
    await page.click('[data-testid="start-session-button"]');
    
    await expect(page.locator('[data-testid="session-status"]')).toHaveText('running', {
      timeout: 15000
    });
    
    // Step 3: Verify events are streaming
    const firstEvent = page.locator('[data-testid="event-item"]').first();
    await expect(firstEvent).toBeVisible({ timeout: 30000 });
    
    // Step 4: Pause session
    await page.click('[data-testid="pause-session-button"]');
    await expect(page.locator('[data-testid="session-status"]')).toHaveText('paused');
    
    // Step 5: Resume session
    await page.click('[data-testid="resume-session-button"]');
    await expect(page.locator('[data-testid="session-status"]')).toHaveText('running');
    
    // Step 6: Stop session
    await page.click('[data-testid="stop-session-button"]');
    await expect(page.locator('[data-testid="session-status"]')).toHaveText('completed');
    
    // Step 7: Verify metrics
    await page.click('[data-testid="view-metrics-button"]');
    await expect(page.locator('[data-testid="total-findings"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-events"]')).toBeVisible();
  });

  test('error boundary catches API failures', async ({ page, context }) => {
    // Intercept and fail API requests
    await context.route('**/api/v1/**', route => route.abort('failed'));
    
    await page.goto('/');
    
    // Should show error boundary
    await expect(page.locator('[data-testid="error-boundary"]')).toBeVisible();
    await expect(page.locator('button:has-text("Retry")')).toBeVisible();
    
    // Restore API and retry
    await context.unroute('**/api/v1/**');
    await page.click('button:has-text("Retry")');
    
    // Should recover
    await expect(page.locator('[data-testid="error-boundary"]')).not.toBeVisible();
  });

  test('session persists across page refresh', async ({ page }) => {
    // Create and start session
    await page.click('[data-testid="new-session-button"]');
    await page.fill('[name="target"]', '192.168.1.1');
    await page.click('button[type="submit"]');
    await page.click('[data-testid="start-session-button"]');
    
    await expect(page.locator('[data-testid="session-status"]')).toHaveText('running');
    
    // Refresh page
    await page.reload();
    
    // Session should still be visible and running
    await expect(page.locator('[data-testid="session-status"]')).toHaveText('running');
  });

  test('WebSocket reconnection on network failure', async ({ page, context }) => {
    // Create session and verify WebSocket connected
    await page.click('[data-testid="new-session-button"]');
    await page.fill('[name="target"]', '192.168.1.1');
    await page.click('button[type="submit"]');
    await page.click('[data-testid="start-session-button"]');
    
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveText('connected');
    
    // Simulate network failure
    await context.setOffline(true);
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveText('disconnected');
    
    // Restore network
    await context.setOffline(false);
    
    // Should reconnect automatically
    await expect(page.locator('[data-testid="websocket-status"]')).toHaveText('connected', {
      timeout: 10000
    });
  });
});
```

---

## 5. Test Execution Schedule

### 5.1 Daily Test Runs

| Day | Focus | Tests | Owner |
|-----|-------|-------|-------|
| 1-2 | Unit tests for new models | Model tests, Repository tests | dev-4 |
| 3-4 | Unit tests for services | Cache, Rate limiter tests | dev-4 |
| 5 | Integration tests | DB persistence, Redis | dev-4 |
| 6 | Frontend unit tests | Error boundary, Hooks | dev-5 |
| 7 | Integration tests | Full stack integration | dev-5 |
| 8-9 | E2E tests | Playwright scenarios | dev-5 |

### 5.2 CI Pipeline Configuration

```yaml
# .github/workflows/test.yml

name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run backend tests
        run: |
          pytest tests/unit -v --cov=src/purple_team_gpt --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run integration tests
        run: |
          pytest tests/integration -v
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Playwright
        run: |
          npm ci
          npx playwright install --with-deps
      
      - name: Run E2E tests
        run: npx playwright test
      
      - name: Upload test artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## 6. Coverage Targets

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| Backend Core | 44% | 80% | P1 |
| Frontend Components | ~30% | 80% | P1 |
| Database Models | 0% | 90% | P0 |
| API Routes | 60% | 85% | P1 |
| WebSocket Handler | 40% | 80% | P1 |
| Error Boundaries | 0% | 100% | P1 |

---

## 7. Test Data Management

### 7.1 Test Fixtures

```python
# tests/fixtures/session_fixtures.py

import pytest
from datetime import datetime

from purple_team_gpt.core.orchestrator import Session, SessionStatus


@pytest.fixture
def pending_session():
    """Create a pending session for testing."""
    return Session(
        id="test-session-pending",
        target="192.168.1.1",
        scope="Authorized test",
        status=SessionStatus.PENDING,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def running_session():
    """Create a running session for testing."""
    session = Session(
        id="test-session-running",
        target="10.0.0.1",
        scope="Production monitoring",
        status=SessionStatus.RUNNING,
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
    )
    return session


@pytest.fixture
def completed_session():
    """Create a completed session with findings."""
    from purple_team_gpt.agents.base import Finding
    
    session = Session(
        id="test-session-completed",
        target="172.16.0.1",
        status=SessionStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(hours=2),
        completed_at=datetime.utcnow(),
    )
    
    session.red_findings = [
        Finding(
            title="Open SSH port",
            severity="medium",
            description="SSH port 22 is exposed",
            tool="nmap",
        )
    ]
    
    session.blue_findings = [
        Finding(
            title="SSH brute force detected",
            severity="high",
            description="Multiple failed login attempts",
            tool="log-analyzer",
        )
    ]
    
    return session
```

---

## 8. Sign-off Checklist

### Pre-Sprint End Verification

- [ ] All unit tests passing
- [ ] Backend coverage >= 80%
- [ ] Frontend coverage >= 80%
- [ ] Integration tests passing
- [ ] E2E tests passing on all browsers
- [ ] No flaky tests in CI
- [ ] Coverage reports generated
- [ ] Test documentation updated

---

**Document Status:** Complete  
**Next Review:** Day 3 Checkpoint