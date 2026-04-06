"""SQLAlchemy/SQLModel database models for Purple Team GPT.

This module defines all database tables for:
- User management (users, roles, permissions)
- Organization management (multi-tenancy)
- Authentication (tokens, API keys)
- Audit logging
- Session management
- Findings and agent states
- Rate limiting

All models use async-compatible SQLAlchemy 2.0 style.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    INET,
    JSONB,
    UUID as PG_UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from purple_team_gpt.db.database import Base


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


# ==================== Enums ====================


class SessionStatus(str, PyEnum):
    """Status of a simulation session."""

    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CLEANING_UP = "cleaning_up"


class AgentType(str, PyEnum):
    """Type of agent."""

    RED = "red"
    BLUE = "blue"
    ORCHESTRATOR = "orchestrator"


class FindingSeverity(str, PyEnum):
    """Severity levels for findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ActorType(str, PyEnum):
    """Type of actor in audit logs."""

    USER = "user"
    SYSTEM = "system"
    API_KEY = "api_key"


class AuditEventType(str, PyEnum):
    """Types of audit events."""

    # Authentication
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"
    TOKEN_REVOKED = "auth.token.revoked"

    # Authorization
    ACCESS_GRANTED = "auth.access.granted"
    ACCESS_DENIED = "auth.access.denied"

    # Sessions
    SESSION_CREATE = "session.create"
    SESSION_START = "session.start"
    SESSION_PAUSE = "session.pause"
    SESSION_RESUME = "session.resume"
    SESSION_STOP = "session.stop"
    SESSION_DELETE = "session.delete"

    # LLM
    LLM_ENDPOINT_ADD = "llm.endpoint.add"
    LLM_ENDPOINT_REMOVE = "llm.endpoint.remove"

    # Admin
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    ROLE_ASSIGN = "role.assign"

    # Security
    RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    INVALID_TOKEN = "security.token.invalid"
    SUSPICIOUS_ACTIVITY = "security.suspicious"


class AuditEventCategory(str, PyEnum):
    """Categories for audit events."""

    AUTH = "auth"
    SESSION = "session"
    LLM = "llm"
    ADMIN = "admin"
    SECURITY = "security"
    TOOL = "tool"


# ==================== User Management ====================


class User(Base):
    """User account model.

    Stores user credentials, profile information, and security settings.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )

    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255))

    # Relationships
    roles: Mapped[List["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="UserRole.user_id"
    )
    organizations: Mapped[List["OrganizationMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMember.user_id",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(back_populates="created_by_user")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="valid_email",
        ),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Role(Base):
    """Role model for RBAC.

    Defines user roles with associated permissions.
    """

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user_roles: Mapped[List["UserRole"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    permissions: Mapped[List["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (CheckConstraint("name ~* '^[a-z_]+$'", name="valid_role_name"),)

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(Base):
    """Permission model for fine-grained access control.

    Defines granular permissions that can be assigned to roles.
    """

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (CheckConstraint("name ~* '^[a-z_:]+$'", name="valid_permission_name"),)

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name})>"


class UserRole(Base):
    """User-Role association table.

    Maps users to their assigned roles.
    """

    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_by: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="roles", foreign_keys=[user_id])
    role: Mapped["Role"] = relationship(back_populates="user_roles")

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class RolePermission(Base):
    """Role-Permission association table.

    Maps roles to their granted permissions.
    """

    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    role: Mapped["Role"] = relationship(back_populates="permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")

    def __repr__(self) -> str:
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


# ==================== Organization (Multi-Tenancy) ====================


class Organization(Base):
    """Organization model for multi-tenant support.

    Organizations group users and resources together.
    """

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Settings
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Limits
    max_sessions: Mapped[int] = mapped_column(Integer, default=10)
    max_users: Mapped[int] = mapped_column(Integer, default=10)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    members: Mapped[List["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    authorized_targets: Mapped[List["AuthorizedTarget"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(back_populates="organization")

    # Constraints
    __table_args__ = (CheckConstraint("slug ~* '^[a-z0-9-]+$'", name="valid_slug"),)

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"


class OrganizationMember(Base):
    """Organization membership association.

    Maps users to organizations with their role within the org.
    """

    __tablename__ = "organization_members"

    org_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Role within organization: 'owner', 'admin', 'member'
    role: Mapped[str] = mapped_column(String(50), default="member")

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    invited_by: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="organizations", foreign_keys=[user_id])

    __table_args__ = (Index("idx_org_members_user", "user_id"),)

    def __repr__(self) -> str:
        return f"<OrganizationMember(org_id={self.org_id}, user_id={self.user_id})>"


class AuthorizedTarget(Base):
    """Authorized target scope for security testing.

    Defines what targets an organization is authorized to test.
    """

    __tablename__ = "authorized_targets"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    org_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )

    # Target definition
    target: Mapped[str] = mapped_column(String(500), nullable=False)
    target_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'ip', 'cidr', 'domain', 'wildcard'

    # Authorization
    scope_document: Mapped[Optional[str]] = mapped_column(Text)
    authorized_by: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    authorized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Validity
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="authorized_targets")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('ip', 'cidr', 'domain', 'wildcard')",
            name="valid_target_type",
        ),
        Index("idx_authorized_targets_active", "org_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<AuthorizedTarget(id={self.id}, target={self.target})>"


# ==================== Authentication ====================


class RefreshToken(Base):
    """Refresh token storage for JWT authentication.

    Stores refresh tokens with device/client tracking.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )

    # Token data
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)  # JWT ID
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Hashed token

    # Owner
    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255))  # Auth session

    # Device/Client info
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # INET as string
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255))

    # Validity
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Revocation
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(50))

    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    use_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    __table_args__ = (Index("idx_refresh_tokens_expires", "expires_at"),)

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"


class APIKey(Base):
    """API key for service account authentication.

    Provides API key based authentication for automation.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )

    # Key data
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )  # First 8 chars for identification

    # Owner
    user_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    org_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )

    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Permissions
    permissions: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Validity
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="api_keys")

    # Constraints
    __table_args__ = (CheckConstraint("length(key_prefix) = 8", name="valid_key_prefix"),)

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name})>"


class LoginHistory(Base):
    """Login history for security auditing.

    Tracks all login attempts for user accounts.
    """

    __tablename__ = "login_history"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Event details
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'login_success', 'login_failure', 'logout', 'token_refresh'

    # Client info
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255))

    # Location (geoIP)
    country: Mapped[Optional[str]] = mapped_column(String(2))
    city: Mapped[Optional[str]] = mapped_column(String(100))

    # Result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (Index("idx_login_history_created", "created_at"),)

    def __repr__(self) -> str:
        return f"<LoginHistory(id={self.id}, user_id={self.user_id}, event_type={self.event_type})>"


# ==================== Audit Logging ====================


class AuditLog(Base):
    """Audit log for security events.

    Immutable audit trail for all security-relevant events.
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )

    # Event identification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Actor
    user_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    org_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        index=True,
    )

    # Actor details
    actor_type: Mapped[str] = mapped_column(String(50), default="user")
    actor_ip: Mapped[Optional[str]] = mapped_column(String(45))
    actor_user_agent: Mapped[Optional[str]] = mapped_column(Text)

    # Resource
    resource_type: Mapped[Optional[str]] = mapped_column(String(100))
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    resource_action: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # 'create', 'read', 'update', 'delete', 'execute'

    # Event data
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Request context
    request_id: Mapped[Optional[str]] = mapped_column(String(255))
    request_method: Mapped[Optional[str]] = mapped_column(String(10))
    request_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamp (immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Retention
    retention_days: Mapped[int] = mapped_column(Integer, default=365)

    __table_args__ = (
        Index("idx_audit_log_resource", "resource_type", "resource_id"),
        Index("idx_audit_log_category", "event_category", "created_at"),
        Index("idx_audit_log_failures", "created_at"),
        Index("idx_audit_log_security", "created_at"),
        CheckConstraint(
            "actor_type IN ('user', 'system', 'api_key')",
            name="valid_actor_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type={self.event_type})>"


# ==================== Sessions ====================


class Session(Base):
    """Simulation session model.

    Replaces the in-memory Session dataclass with persistent storage.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )

    # Target
    target: Mapped[str] = mapped_column(String(500), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Ownership
    org_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Agents status
    red_agent_status: Mapped[str] = mapped_column(String(20), default="idle")
    blue_agent_status: Mapped[str] = mapped_column(String(20), default="idle")

    # Findings summary
    red_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    blue_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    high_findings_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metrics
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Metadata
    session_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, name="metadata")
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Initialization error
    initialization_error: Mapped[Optional[str]] = mapped_column(Text)

    # Retention
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(back_populates="sessions")
    created_by_user: Mapped[Optional["User"]] = relationship(back_populates="sessions")
    events: Mapped[List["SessionEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    findings: Mapped[List["Finding"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    agent_states: Mapped[List["AgentState"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'initializing', 'running', 'paused', 'completed', 'error', 'cleaning_up')",
            name="valid_session_status",
        ),
        Index("idx_sessions_active", "org_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, target={self.target}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            "id": self.id,
            "target": self.target,
            "scope": self.scope,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_activity_at": self.last_activity_at.isoformat()
            if self.last_activity_at
            else None,
            "red_findings_count": self.red_findings_count,
            "blue_findings_count": self.blue_findings_count,
            "total_events": self.total_events,
            "initialization_error": self.initialization_error,
        }


class SessionEvent(Base):
    """Event emitted during session execution.

    Records all events from agents during a simulation session.
    """

    __tablename__ = "session_events"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    session_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )

    # Event details
    agent: Mapped[str] = mapped_column(String(20), nullable=False)  # 'red', 'blue', 'orchestrator'
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Event data
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="events")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "agent IN ('red', 'blue', 'orchestrator')",
            name="valid_agent",
        ),
        Index("idx_session_events_session", "session_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SessionEvent(id={self.id}, session_id={self.session_id}, event_type={self.event_type})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "session_id": self.session_id,
            "agent": self.agent,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
        }


class Finding(Base):
    """Security finding from an agent.

    Records vulnerabilities, misconfigurations, or detections found during assessment.
    """

    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    session_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )

    # Finding details
    agent: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    evidence: Mapped[Optional[str]] = mapped_column(Text)
    recommendation: Mapped[Optional[str]] = mapped_column(Text)

    # Classification
    cve: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    cvss_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1))
    category: Mapped[Optional[str]] = mapped_column(String(100))

    # Tool
    tool: Mapped[Optional[str]] = mapped_column(String(100))
    raw_output: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    finding_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, name="metadata")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Verification
    verified_by: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_false_positive: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="findings")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low', 'info')",
            name="valid_severity",
        ),
        CheckConstraint(
            "agent IN ('red', 'blue')",
            name="valid_finding_agent",
        ),
        Index("idx_findings_severity", "session_id", "severity"),
    )

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, title={self.title}, severity={self.severity})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent": self.agent,
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "cve": self.cve,
            "cvss_score": float(self.cvss_score) if self.cvss_score else None,
            "category": self.category,
            "tool": self.tool,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
        }


class AgentState(Base):
    """Agent state persistence for session recovery.

    Stores the state of agents during a session for recovery and analysis.
    """

    __tablename__ = "agent_states"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    session_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )

    # Agent identification
    agent_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'red', 'blue'

    # State data
    state: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'idle', 'running', 'paused', 'completed', 'error'
    conversation_history: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="agent_states")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "agent_type IN ('red', 'blue')",
            name="valid_agent_type",
        ),
        CheckConstraint(
            "state IN ('idle', 'running', 'paused', 'completed', 'error')",
            name="valid_agent_state",
        ),
        UniqueConstraint("session_id", "agent_type", name="uq_session_agent"),
    )

    def __repr__(self) -> str:
        return f"<AgentState(id={self.id}, session_id={self.session_id}, agent_type={self.agent_type})>"


# ==================== Rate Limiting ====================


class RateLimitBan(Base):
    """Rate limit violation tracking.

    Records bans imposed for rate limit violations.
    """

    __tablename__ = "rate_limit_bans"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )

    # Identification
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Ban details
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    ban_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'temporary', 'permanent'

    # Validity
    banned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Metadata
    request_count: Mapped[Optional[int]] = mapped_column(Integer)
    threshold: Mapped[Optional[int]] = mapped_column(Integer)

    # Unban
    unbanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    unbanned_by: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    unban_reason: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "ban_type IN ('temporary', 'permanent')",
            name="valid_ban_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<RateLimitBan(id={self.id}, reason={self.reason})>"


# ==================== Default Data ====================

DEFAULT_ROLES = [
    {"name": "admin", "description": "Full system administrator", "is_system": True},
    {"name": "analyst", "description": "Security analyst with execution rights", "is_system": True},
    {"name": "viewer", "description": "Read-only access", "is_system": True},
    {"name": "service", "description": "Service account for automation", "is_system": True},
]

DEFAULT_PERMISSIONS = [
    # Session permissions
    {"name": "sessions:read", "description": "View session details", "category": "sessions"},
    {"name": "sessions:write", "description": "Create and modify sessions", "category": "sessions"},
    {"name": "sessions:delete", "description": "Delete sessions", "category": "sessions"},
    {
        "name": "sessions:execute",
        "description": "Start, pause, resume, stop sessions",
        "category": "sessions",
    },
    # Finding permissions
    {"name": "findings:read", "description": "View security findings", "category": "findings"},
    {"name": "findings:write", "description": "Create and modify findings", "category": "findings"},
    {
        "name": "findings:export",
        "description": "Export findings to external formats",
        "category": "findings",
    },
    # LLM permissions
    {"name": "llm:configure", "description": "Configure LLM endpoints", "category": "llm"},
    {"name": "llm:test", "description": "Test LLM connections", "category": "llm"},
    # User management
    {"name": "users:manage", "description": "Create, modify, delete users", "category": "users"},
    {"name": "users:read", "description": "View user profiles", "category": "users"},
    # Audit
    {"name": "audit:read", "description": "View audit logs", "category": "audit"},
    # System
    {"name": "system:configure", "description": "Modify system settings", "category": "system"},
]

# Role-permission assignments
ROLE_PERMISSIONS = {
    "admin": [p["name"] for p in DEFAULT_PERMISSIONS],  # All permissions
    "analyst": [
        "sessions:read",
        "sessions:write",
        "sessions:execute",
        "findings:read",
        "findings:write",
        "findings:export",
        "llm:test",
    ],
    "viewer": ["sessions:read", "findings:read"],
    "service": [
        "sessions:read",
        "sessions:write",
        "sessions:execute",
        "findings:read",
        "findings:write",
    ],
}


__all__ = [
    # Enums
    "SessionStatus",
    "AgentType",
    "FindingSeverity",
    "ActorType",
    "AuditEventType",
    "AuditEventCategory",
    # Models
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "Organization",
    "OrganizationMember",
    "AuthorizedTarget",
    "RefreshToken",
    "APIKey",
    "LoginHistory",
    "AuditLog",
    "Session",
    "SessionEvent",
    "Finding",
    "AgentState",
    "RateLimitBan",
    # Default data
    "DEFAULT_ROLES",
    "DEFAULT_PERMISSIONS",
    "ROLE_PERMISSIONS",
]
