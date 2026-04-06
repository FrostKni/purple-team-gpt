# Database Architecture

## Overview

Purple Team GPT uses PostgreSQL with SQLAlchemy async for persistent storage. This document describes the database architecture, connection pooling, and migration strategy.

## Schema Design

### Core Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts and credentials |
| `roles` | Role definitions for RBAC |
| `permissions` | Fine-grained permissions |
| `user_roles` | User-role assignments |
| `role_permissions` | Role-permission assignments |
| `organizations` | Multi-tenant organization support |
| `organization_members` | User-organization membership |
| `authorized_targets` | Target scope authorization |
| `refresh_tokens` | Refresh token storage |
| `api_keys` | Service account API keys |
| `login_history` | Login attempt history |
| `audit_log` | Immutable security audit trail |
| `sessions` | Simulation sessions (replaces in-memory) |
| `session_events` | Events during session execution |
| `findings` | Security findings from agents |
| `agent_states` | Agent state for recovery |
| `rate_limit_bans` | Rate limit violation tracking |

## Connection Pooling

Configuration via environment variables:

```bash
# Database URL
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Pool settings
DB_POOL_SIZE=10          # Number of permanent connections
DB_MAX_OVERFLOW=20       # Additional connections during spikes
DB_POOL_TIMEOUT=30       # Seconds to wait for connection
DB_POOL_RECYCLE=3600     # Recycle connections after 1 hour
DB_POOL_PRE_PING=true    # Verify connections before use

# Development/Testing
DB_USE_NULL_POOL=false   # Disable pooling for serverless
DB_ECHO=false            # Log SQL queries
```

### Session Management Pattern

```python
from purple_team_gpt.db import get_async_session, SessionRepository

# FastAPI endpoint
@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    repo = SessionRepository(db)
    session = await repo.get_session(session_id)
    return session

# Background tasks
async with get_session_context() as session:
    repo = SessionRepository(session)
    await repo.create_session(target="192.168.1.1")
```

## Migration Strategy

### Running Migrations

```bash
# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "description"

# View migration history
alembic history
```

### Migration from In-Memory to Persistent

1. **Phase 1: Dual-Write** - Write to both in-memory and database
2. **Phase 2: Read from DB** - Read operations use database
3. **Phase 3: Remove In-Memory** - Deprecate in-memory storage

## Security Features

### Row-Level Security (Future)
- Organization isolation via PostgreSQL RLS
- User-based access control

### Audit Logging
- Immutable audit trail
- Retention policies
- Event categorization

### Data Validation
- Email format validation via CHECK constraints
- Role/permission name format validation
- Status enum validation

## Performance Considerations

### Indexes

Key indexes for common queries:
- `idx_sessions_active` - Active sessions by org
- `idx_audit_log_created` - Time-ordered audit logs
- `idx_findings_severity` - Findings by severity
- Partial indexes for filtered queries

### Partitioning (Future)

For large-scale deployments:
- Audit log partitioning by month
- Session events partitioning by session

## Backup Strategy

1. **Full Backup** - Daily pg_dump
2. **WAL Archiving** - Point-in-time recovery
3. **Audit Log Retention** - 365 days default

## Environment Configuration

```bash
# Required
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/purple_team_gpt

# Optional
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_ECHO=false
```

## Development Setup

```bash
# Start PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=purple_team_gpt \
  -p 5432:5432 \
  postgres:15

# Run migrations
cd purple-team-gpt
alembic upgrade head
```