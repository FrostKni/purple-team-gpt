# Database Schema Updates

## Overview

This document outlines the database schema changes required to support the new security architecture, including user management, authentication, sessions, and audit logging.

## 1. Schema Migration Summary

### New Tables Required

| Table | Purpose |
|-------|---------|
| `users` | User accounts and credentials |
| `api_keys` | Service account API keys |
| `organizations` | Multi-tenant organization support |
| `organization_members` | User-organization membership |
| `refresh_tokens` | Refresh token storage |
| `audit_log` | Security audit trail |
| `sessions_v2` | Enhanced session metadata |
| `authorized_targets` | Target scope authorization |
| `rate_limit_bans` | Rate limit violation tracking |

### Existing Tables to Modify

| Table | Changes |
|-------|---------|
| `feedback_entries` | Add `org_id`, `created_by` columns |
| Session storage | Add org isolation |

---

## 2. User Management Schema

### 2.1 Users Table

```sql
-- src/purple_team_gpt/models/user.py

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    -- Security
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    
    -- Constraints
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Comments
COMMENT ON TABLE users IS 'User accounts for authentication';
COMMENT ON COLUMN users.password_hash IS 'bcrypt hashed password';
COMMENT ON COLUMN users.failed_login_attempts IS 'Count of failed login attempts (reset on success)';
```

### 2.2 Roles Table

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    
    -- Built-in roles cannot be modified
    is_system BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_role_name CHECK (name ~* '^[a-z_]+$')
);

-- Insert default roles
INSERT INTO roles (name, description, is_system) VALUES
    ('admin', 'Full system administrator', TRUE),
    ('analyst', 'Security analyst with execution rights', TRUE),
    ('viewer', 'Read-only access', TRUE),
    ('service', 'Service account for automation', TRUE);
```

### 2.3 Permissions Table

```sql
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_permission_name CHECK (name ~* '^[a-z_:]+$')
);

-- Insert default permissions
INSERT INTO permissions (name, description, category) VALUES
    -- Session permissions
    ('sessions:read', 'View session details', 'sessions'),
    ('sessions:write', 'Create and modify sessions', 'sessions'),
    ('sessions:delete', 'Delete sessions', 'sessions'),
    ('sessions:execute', 'Start, pause, resume, stop sessions', 'sessions'),
    
    -- Finding permissions
    ('findings:read', 'View security findings', 'findings'),
    ('findings:write', 'Create and modify findings', 'findings'),
    ('findings:export', 'Export findings to external formats', 'findings'),
    
    -- LLM permissions
    ('llm:configure', 'Configure LLM endpoints', 'llm'),
    ('llm:test', 'Test LLM connections', 'llm'),
    
    -- User management
    ('users:manage', 'Create, modify, delete users', 'users'),
    ('users:read', 'View user profiles', 'users'),
    
    -- Audit
    ('audit:read', 'View audit logs', 'audit'),
    
    -- System
    ('system:configure', 'Modify system settings', 'system');
```

### 2.4 Role-Permission Mapping

```sql
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    
    PRIMARY KEY (role_id, permission_id)
);

-- Assign permissions to roles
-- Admin has all permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'admin';

-- Analyst permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'analyst' 
AND p.name IN (
    'sessions:read', 'sessions:write', 'sessions:execute',
    'findings:read', 'findings:write', 'findings:export',
    'llm:test'
);

-- Viewer permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'viewer' 
AND p.name IN ('sessions:read', 'findings:read');

-- Service permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p 
WHERE r.name = 'service' 
AND p.name IN (
    'sessions:read', 'sessions:write', 'sessions:execute',
    'findings:read', 'findings:write'
);
```

### 2.5 User Roles

```sql
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
```

---

## 3. Organization Schema (Multi-Tenancy)

### 3.1 Organizations Table

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    
    -- Settings
    settings JSONB DEFAULT '{}',
    
    -- Limits
    max_sessions INTEGER DEFAULT 10,
    max_users INTEGER DEFAULT 10,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_slug CHECK (slug ~* '^[a-z0-9-]+$')
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
```

### 3.2 Organization Members

```sql
CREATE TABLE organization_members (
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    role VARCHAR(50) DEFAULT 'member', -- 'owner', 'admin', 'member'
    
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    invited_by UUID REFERENCES users(id),
    
    PRIMARY KEY (org_id, user_id)
);

CREATE INDEX idx_org_members_user ON organization_members(user_id);
```

### 3.3 Authorized Targets

```sql
CREATE TABLE authorized_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Target definition
    target VARCHAR(500) NOT NULL,  -- IP, CIDR, domain, wildcard
    target_type VARCHAR(20) NOT NULL, -- 'ip', 'cidr', 'domain', 'wildcard'
    
    -- Authorization
    scope_document TEXT,  -- Authorization document reference
    authorized_by UUID REFERENCES users(id),
    authorized_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Validity
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    description TEXT,
    tags JSONB DEFAULT '[]',
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_target_type CHECK (target_type IN ('ip', 'cidr', 'domain', 'wildcard'))
);

CREATE INDEX idx_authorized_targets_org ON authorized_targets(org_id);
CREATE INDEX idx_authorized_targets_active ON authorized_targets(org_id, is_active) WHERE is_active = TRUE;
```

---

## 4. Authentication Schema

### 4.1 Refresh Tokens Table

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Token data
    jti VARCHAR(255) UNIQUE NOT NULL,  -- JWT ID
    token_hash VARCHAR(255) NOT NULL,  -- Hashed token for lookup
    
    -- Owner
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255),  -- Auth session, not Purple Team session
    
    -- Device/Client info
    user_agent TEXT,
    ip_address INET,
    device_fingerprint VARCHAR(255),
    
    -- Validity
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Revocation
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_reason VARCHAR(50),
    
    -- Usage tracking
    last_used_at TIMESTAMP WITH TIME ZONE,
    use_count INTEGER DEFAULT 0
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_jti ON refresh_tokens(jti);
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at) WHERE is_revoked = FALSE;
```

### 4.2 API Keys Table

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Key data
    key_hash VARCHAR(255) UNIQUE NOT NULL,  -- Hashed API key
    key_prefix VARCHAR(10) NOT NULL,  -- First 8 chars for identification
    
    -- Owner
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Metadata
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Permissions
    permissions JSONB DEFAULT '[]',  -- List of permission strings
    
    -- Validity
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT valid_key_prefix CHECK (length(key_prefix) = 8)
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
```

### 4.3 Login History

```sql
CREATE TABLE login_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Event details
    event_type VARCHAR(50) NOT NULL, -- 'login_success', 'login_failure', 'logout', 'token_refresh'
    
    -- Client info
    ip_address INET,
    user_agent TEXT,
    device_fingerprint VARCHAR(255),
    
    -- Location (geoIP)
    country VARCHAR(2),
    city VARCHAR(100),
    
    -- Result
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_login_history_user ON login_history(user_id);
CREATE INDEX idx_login_history_created ON login_history(created_at DESC);
```

---

## 5. Audit Log Schema

### 5.1 Audit Log Table

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event identification
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50) NOT NULL, -- 'auth', 'session', 'llm', 'admin', 'security'
    
    -- Actor
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    
    -- Actor details
    actor_type VARCHAR(50) DEFAULT 'user', -- 'user', 'system', 'api_key'
    actor_ip INET,
    actor_user_agent TEXT,
    
    -- Resource
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_action VARCHAR(50), -- 'create', 'read', 'update', 'delete', 'execute'
    
    -- Event data
    details JSONB DEFAULT '{}',
    
    -- Request context
    request_id VARCHAR(255),
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    
    -- Result
    success BOOLEAN NOT NULL,
    error_message TEXT,
    
    -- Timestamp (immutable)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Retention
    retention_days INTEGER DEFAULT 365
);

-- Indexes for common queries
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_org ON audit_log(org_id);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_category ON audit_log(event_category, created_at DESC);

-- Partial indexes for common filters
CREATE INDEX idx_audit_log_failures ON audit_log(created_at DESC) WHERE success = FALSE;
CREATE INDEX idx_audit_log_security ON audit_log(created_at DESC) WHERE event_category = 'security';

-- Partitioning for large-scale deployments
-- (PostgreSQL 10+)
-- CREATE TABLE audit_log_2024_01 PARTITION OF audit_log
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

COMMENT ON TABLE audit_log IS 'Immutable audit trail for security events';
```

### 5.2 Audit Archive Table

```sql
CREATE TABLE audit_archive (
    id UUID PRIMARY KEY,
    
    -- Same structure as audit_log
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    user_id UUID,
    org_id UUID,
    actor_type VARCHAR(50),
    actor_ip INET,
    actor_user_agent TEXT,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_action VARCHAR(50),
    details JSONB,
    request_id VARCHAR(255),
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Archive metadata
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archive_batch VARCHAR(100)
);

-- No indexes on archive (cold storage)
```

---

## 6. Session Schema Updates

### 6.1 Enhanced Sessions Table

```sql
-- Add columns to existing session storage
-- If using ChromaDB for sessions, consider moving to SQL for better querying

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Target
    target VARCHAR(500) NOT NULL,
    scope TEXT NOT NULL,
    
    -- Ownership
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Agents
    red_agent_status VARCHAR(20) DEFAULT 'idle',
    blue_agent_status VARCHAR(20) DEFAULT 'idle',
    
    -- Findings summary
    red_findings_count INTEGER DEFAULT 0,
    blue_findings_count INTEGER DEFAULT 0,
    critical_findings_count INTEGER DEFAULT 0,
    high_findings_count INTEGER DEFAULT 0,
    
    -- Metrics
    total_steps INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    duration_seconds INTEGER,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]',
    
    -- Retention
    expires_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'paused', 'completed', 'error'))
);

CREATE INDEX idx_sessions_org ON sessions(org_id);
CREATE INDEX idx_sessions_created_by ON sessions(created_by);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created ON sessions(created_at DESC);
CREATE INDEX idx_sessions_active ON sessions(org_id, status) WHERE status IN ('pending', 'running', 'paused');
```

### 6.2 Session Events Table

```sql
CREATE TABLE session_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Event details
    agent VARCHAR(20) NOT NULL, -- 'red', 'blue', 'orchestrator'
    event_type VARCHAR(100) NOT NULL,
    
    -- Event data
    data JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_agent CHECK (agent IN ('red', 'blue', 'orchestrator'))
);

CREATE INDEX idx_session_events_session ON session_events(session_id, created_at);
CREATE INDEX idx_session_events_type ON session_events(session_id, event_type);
```

### 6.3 Findings Table

```sql
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Finding details
    agent VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    evidence TEXT,
    recommendation TEXT,
    
    -- Classification
    cve VARCHAR(50),
    cvss_score DECIMAL(3, 1),
    category VARCHAR(100),
    
    -- Tool
    tool VARCHAR(100),
    raw_output TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Verification
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMP WITH TIME ZONE,
    is_false_positive BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT valid_severity CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    CONSTRAINT valid_agent CHECK (agent IN ('red', 'blue'))
);

CREATE INDEX idx_findings_session ON findings(session_id);
CREATE INDEX idx_findings_severity ON findings(session_id, severity);
CREATE INDEX idx_findings_cve ON findings(cve) WHERE cve IS NOT NULL;
```

---

## 7. Rate Limiting Schema

### 7.1 Rate Limit Bans Table

```sql
CREATE TABLE rate_limit_bans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    ip_address INET,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Ban details
    reason VARCHAR(100) NOT NULL,
    ban_type VARCHAR(50) NOT NULL, -- 'temporary', 'permanent'
    
    -- Validity
    banned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    request_count INTEGER,
    threshold INTEGER,
    
    -- Unban
    unbanned_at TIMESTAMP WITH TIME ZONE,
    unbanned_by UUID REFERENCES users(id),
    unban_reason TEXT,
    
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_rate_bans_ip ON rate_limit_bans(ip_address) WHERE is_active = TRUE;
CREATE INDEX idx_rate_bans_user ON rate_limit_bans(user_id) WHERE is_active = TRUE;
```

---

## 8. SQLModel Definitions

### 8.1 User Models

```python
# src/purple_team_gpt/models/user.py

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class UserBase(SQLModel):
    """Base user fields."""
    email: str = Field(sa_column=Column(String(255), unique=True, nullable=False))
    full_name: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)


class User(UserBase, table=True):
    """User account model."""
    
    __tablename__ = "users"
    
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    password_hash: str = Field(sa_column=Column(String(255), nullable=False))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = Field(default=None)
    
    # Security
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None)
    mfa_enabled: bool = Field(default=False)
    mfa_secret: Optional[str] = Field(default=None)
    
    # Relationships
    roles: List["UserRole"] = Relationship(back_populates="user")
    organizations: List["OrganizationMember"] = Relationship(back_populates="user")


class UserCreate(SQLModel):
    """User creation request."""
    email: str
    password: str
    full_name: Optional[str] = None


class UserUpdate(SQLModel):
    """User update request."""
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    """User response model."""
    id: str
    created_at: datetime
    roles: List[str] = []


class UserRole(SQLModel, table=True):
    """User-Role association."""
    
    __tablename__ = "user_roles"
    
    user_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    )
    role_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    )
    granted_by: Optional[str] = Field(default=None)
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="roles")
    role: "Role" = Relationship()


class Role(SQLModel, table=True):
    """Role model."""
    
    __tablename__ = "roles"
    
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    name: str = Field(sa_column=Column(String(50), unique=True, nullable=False))
    description: Optional[str] = Field(default=None)
    is_system: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    permissions: List["RolePermission"] = Relationship(back_populates="role")


class Permission(SQLModel, table=True):
    """Permission model."""
    
    __tablename__ = "permissions"
    
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    name: str = Field(sa_column=Column(String(100), unique=True, nullable=False))
    description: Optional[str] = Field(default=None)
    category: str = Field(sa_column=Column(String(50), nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RolePermission(SQLModel, table=True):
    """Role-Permission association."""
    
    __tablename__ = "role_permissions"
    
    role_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    )
    permission_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True),
    )
    
    role: Role = Relationship(back_populates="permissions")
```

### 8.2 Audit Model

```python
# src/purple_team_gpt/models/audit.py

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB, INET


class AuditEventType(str, Enum):
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


class AuditEventCategory(str, Enum):
    """Categories for audit events."""
    AUTH = "auth"
    SESSION = "session"
    LLM = "llm"
    ADMIN = "admin"
    SECURITY = "security"
    TOOL = "tool"


class AuditLog(SQLModel, table=True):
    """Audit log entry."""
    
    __tablename__ = "audit_log"
    
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    
    # Event identification
    event_type: str = Field(sa_column=Column(String(100), nullable=False))
    event_category: str = Field(sa_column=Column(String(50), nullable=False))
    
    # Actor
    user_id: Optional[str] = Field(default=None)
    org_id: Optional[str] = Field(default=None)
    actor_type: str = Field(default="user")
    actor_ip: Optional[str] = Field(default=None)
    actor_user_agent: Optional[str] = Field(default=None)
    
    # Resource
    resource_type: Optional[str] = Field(default=None)
    resource_id: Optional[str] = Field(default=None)
    resource_action: Optional[str] = Field(default=None)
    
    # Event data
    details: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    
    # Request context
    request_id: Optional[str] = Field(default=None)
    request_method: Optional[str] = Field(default=None)
    request_path: Optional[str] = Field(default=None)
    
    # Result
    success: bool = Field(nullable=False)
    error_message: Optional[str] = Field(default=None)
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Retention
    retention_days: int = Field(default=365)


class AuditLogCreate(SQLModel):
    """Model for creating audit log entries."""
    event_type: AuditEventType
    event_category: AuditEventCategory
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    actor_type: str = "user"
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_action: Optional[str] = None
    details: Dict[str, Any] = {}
    request_id: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
```

---

## 9. Migration Scripts

### 9.1 Initial Migration

```python
# alembic/versions/001_security_schema.py

"""Security schema migration

Revision ID: 001
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime),
        sa.Column('failed_login_attempts', sa.Integer, default=0),
        sa.Column('locked_until', sa.DateTime),
        sa.Column('mfa_enabled', sa.Boolean, default=False),
        sa.Column('mfa_secret', sa.String(255)),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    
    # Create role_permissions junction table
    op.create_table(
        'role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id'), primary_key=True),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('permissions.id'), primary_key=True),
    )
    
    # Create user_roles junction table
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id'), primary_key=True),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('granted_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    
    # Insert default roles and permissions
    op.execute("""
        INSERT INTO roles (id, name, description, is_system) VALUES
            (uuid_generate_v4(), 'admin', 'Full system administrator', TRUE),
            (uuid_generate_v4(), 'analyst', 'Security analyst', TRUE),
            (uuid_generate_v4(), 'viewer', 'Read-only access', TRUE),
            (uuid_generate_v4(), 'service', 'Service account', TRUE);
    """)
    
    # ... continue with other tables


def downgrade():
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('users')
    op.drop_table('permissions')
    op.drop_table('roles')
```

---

## 10. Database Best Practices

### 10.1 Security Considerations

1. **Password Storage**: Use bcrypt with cost factor 12+
2. **API Keys**: Store only hashed values (SHA-256)
3. **Sensitive Data**: Consider encryption at rest with application-level encryption
4. **Connection Security**: Use SSL/TLS for all database connections
5. **Credential Management**: Use environment variables or secret management

### 10.2 Performance Considerations

1. **Indexing**: Add indexes for all foreign keys and commonly queried fields
2. **Partitioning**: Partition audit_log by time for large deployments
3. **Connection Pooling**: Use PgBouncer or built-in pooling
4. **Read Replicas**: Use read replicas for analytics queries

### 10.3 Retention Policies

```sql
-- Create retention policy function
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM audit_log 
    WHERE created_at < NOW() - (retention_days || ' days')::interval;
END;
$$ LANGUAGE plpgsql;

-- Schedule with pg_cron extension
-- SELECT cron.schedule('cleanup_audit', '0 2 * * *', 'SELECT cleanup_old_audit_logs()');
```

---

## 11. Implementation Checklist

- [ ] Create database migrations
- [ ] Implement SQLModel models
- [ ] Create user registration endpoint
- [ ] Implement password hashing
- [ ] Create role/permission seed data
- [ ] Implement RBAC queries
- [ ] Create audit logging triggers
- [ ] Set up database backups
- [ ] Configure connection pooling
- [ ] Create retention policies