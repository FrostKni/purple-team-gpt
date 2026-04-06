"""Database package for Purple Team GPT.

This package provides PostgreSQL persistence layer using SQLAlchemy async.

Modules:
    - database: Async engine, session management, connection pooling
    - models: SQLModel/SQLAlchemy models for all entities
    - repository: Repository pattern for database operations
"""

from purple_team_gpt.db.database import (
    async_engine,
    AsyncSessionLocal,
    get_async_session,
    get_session_context,
    init_db,
    close_db,
    check_db_connection,
    create_engine,
    DatabaseSessionManager,
    Base,
)
from purple_team_gpt.db.models import (
    # Enums
    SessionStatus,
    AgentType,
    FindingSeverity,
    ActorType,
    AuditEventType,
    AuditEventCategory,
    # User Management
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    # Organization
    Organization,
    OrganizationMember,
    AuthorizedTarget,
    # Authentication
    RefreshToken,
    APIKey,
    LoginHistory,
    # Audit
    AuditLog,
    # Sessions
    Session,
    SessionEvent,
    Finding,
    AgentState,
    # Rate Limiting
    RateLimitBan,
    # Default Data
    DEFAULT_ROLES,
    DEFAULT_PERMISSIONS,
    ROLE_PERMISSIONS,
)
from purple_team_gpt.db.repository import (
    SessionRepository,
    AuditRepository,
    UserRepository,
)

__all__ = [
    # Database
    "async_engine",
    "AsyncSessionLocal",
    "get_async_session",
    "get_session_context",
    "init_db",
    "close_db",
    "check_db_connection",
    "create_engine",
    "DatabaseSessionManager",
    "Base",
    # Enums
    "SessionStatus",
    "AgentType",
    "FindingSeverity",
    "ActorType",
    "AuditEventType",
    "AuditEventCategory",
    # User Management
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    # Organization
    "Organization",
    "OrganizationMember",
    "AuthorizedTarget",
    # Authentication
    "RefreshToken",
    "APIKey",
    "LoginHistory",
    # Audit
    "AuditLog",
    # Sessions
    "Session",
    "SessionEvent",
    "Finding",
    "AgentState",
    # Rate Limiting
    "RateLimitBan",
    # Default Data
    "DEFAULT_ROLES",
    "DEFAULT_PERMISSIONS",
    "ROLE_PERMISSIONS",
    # Repositories
    "SessionRepository",
    "AuditRepository",
    "UserRepository",
]