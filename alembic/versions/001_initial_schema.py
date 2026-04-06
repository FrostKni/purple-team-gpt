"""Initial database schema for Purple Team GPT.

Creates all tables for:
- User management (users, roles, permissions, user_roles, role_permissions)
- Organization management (organizations, organization_members, authorized_targets)
- Authentication (refresh_tokens, api_keys, login_history)
- Audit logging (audit_log)
- Session management (sessions, session_events)
- Findings (findings, agent_states)
- Rate limiting (rate_limit_bans)

Revision ID: 001
Revises: 
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # ==================== Roles ====================
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("name ~* '^[a-z_]+$'", name='valid_role_name'),
    )
    
    # ==================== Permissions ====================
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("name ~* '^[a-z_:]+$'", name='valid_permission_name'),
    )
    
    # ==================== Users ====================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('failed_login_attempts', sa.Integer, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('mfa_enabled', sa.Boolean, default=False),
        sa.Column('mfa_secret', sa.String(255)),
        sa.CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name='valid_email',
        ),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_active', 'users', ['is_active'])
    
    # ==================== Role Permissions ====================
    op.create_table(
        'role_permissions',
        sa.Column(
            'role_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('roles.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        sa.Column(
            'permission_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('permissions.id', ondelete='CASCADE'),
            primary_key=True,
        ),
    )
    
    # ==================== User Roles ====================
    op.create_table(
        'user_roles',
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        sa.Column(
            'role_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('roles.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        sa.Column(
            'granted_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
        ),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_role', 'user_roles', ['role_id'])
    
    # ==================== Organizations ====================
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('max_sessions', sa.Integer, default=10),
        sa.Column('max_users', sa.Integer, default=10),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("slug ~* '^[a-z0-9-]+$'", name='valid_slug'),
    )
    op.create_index('idx_organizations_slug', 'organizations', ['slug'])
    
    # ==================== Organization Members ====================
    op.create_table(
        'organization_members',
        sa.Column(
            'org_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('organizations.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        sa.Column('role', sa.String(50), default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            'invited_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
        ),
    )
    op.create_index('idx_org_members_user', 'organization_members', ['user_id'])
    
    # ==================== Authorized Targets ====================
    op.create_table(
        'authorized_targets',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'org_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('organizations.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('target', sa.String(500), nullable=False),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('scope_document', sa.Text),
        sa.Column(
            'authorized_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
        ),
        sa.Column('authorized_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('valid_from', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime(timezone=True)),
        sa.Column('description', sa.Text),
        sa.Column('tags', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "target_type IN ('ip', 'cidr', 'domain', 'wildcard')",
            name='valid_target_type',
        ),
    )
    op.create_index('idx_authorized_targets_org', 'authorized_targets', ['org_id'])
    op.create_index('idx_authorized_targets_active', 'authorized_targets', ['org_id', 'is_active'])
    
    # ==================== Refresh Tokens ====================
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('jti', sa.String(255), unique=True, nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('session_id', sa.String(255)),
        sa.Column('user_agent', sa.Text),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('device_fingerprint', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean, default=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_reason', sa.String(50)),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('use_count', sa.Integer, default=0),
    )
    op.create_index('idx_refresh_tokens_user', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_jti', 'refresh_tokens', ['jti'])
    op.create_index('idx_refresh_tokens_expires', 'refresh_tokens', ['expires_at'])
    
    # ==================== API Keys ====================
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('key_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('key_prefix', sa.String(10), nullable=False),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
        ),
        sa.Column(
            'org_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('organizations.id', ondelete='CASCADE'),
        ),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('permissions', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.CheckConstraint('length(key_prefix) = 8', name='valid_key_prefix'),
    )
    op.create_index('idx_api_keys_hash', 'api_keys', ['key_hash'])
    op.create_index('idx_api_keys_user', 'api_keys', ['user_id'])
    op.create_index('idx_api_keys_prefix', 'api_keys', ['key_prefix'])
    
    # ==================== Login History ====================
    op.create_table(
        'login_history',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
        ),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text),
        sa.Column('device_fingerprint', sa.String(255)),
        sa.Column('country', sa.String(2)),
        sa.Column('city', sa.String(100)),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('failure_reason', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_login_history_user', 'login_history', ['user_id'])
    op.create_index('idx_login_history_created', 'login_history', ['created_at'])
    
    # ==================== Audit Log ====================
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_category', sa.String(50), nullable=False),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
        ),
        sa.Column(
            'org_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('organizations.id', ondelete='SET NULL'),
        ),
        sa.Column('actor_type', sa.String(50), default='user'),
        sa.Column('actor_ip', sa.String(45)),
        sa.Column('actor_user_agent', sa.Text),
        sa.Column('resource_type', sa.String(100)),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('resource_action', sa.String(50)),
        sa.Column('details', postgresql.JSONB, default={}),
        sa.Column('request_id', sa.String(255)),
        sa.Column('request_method', sa.String(10)),
        sa.Column('request_path', sa.String(500)),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('retention_days', sa.Integer, default=365),
        sa.CheckConstraint(
            "actor_type IN ('user', 'system', 'api_key')",
            name='valid_actor_type',
        ),
    )
    op.create_index('idx_audit_log_user', 'audit_log', ['user_id'])
    op.create_index('idx_audit_log_org', 'audit_log', ['org_id'])
    op.create_index('idx_audit_log_event_type', 'audit_log', ['event_type'])
    op.create_index('idx_audit_log_resource', 'audit_log', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_log_created', 'audit_log', ['created_at'])
    op.create_index('idx_audit_log_category', 'audit_log', ['event_category', 'created_at'])
    # Partial indexes for common filters
    op.execute(
        "CREATE INDEX idx_audit_log_failures ON audit_log (created_at DESC) WHERE success = FALSE"
    )
    op.execute(
        "CREATE INDEX idx_audit_log_security ON audit_log (created_at DESC) WHERE event_category = 'security'"
    )
    
    # ==================== Sessions ====================
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('target', sa.String(500), nullable=False),
        sa.Column('scope', sa.Text, nullable=False, default=''),
        sa.Column(
            'org_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('organizations.id', ondelete='CASCADE'),
        ),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
        ),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('red_agent_status', sa.String(20), default='idle'),
        sa.Column('blue_agent_status', sa.String(20), default='idle'),
        sa.Column('red_findings_count', sa.Integer, default=0),
        sa.Column('blue_findings_count', sa.Integer, default=0),
        sa.Column('critical_findings_count', sa.Integer, default=0),
        sa.Column('high_findings_count', sa.Integer, default=0),
        sa.Column('total_steps', sa.Integer, default=0),
        sa.Column('total_events', sa.Integer, default=0),
        sa.Column('duration_seconds', sa.Integer),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('tags', postgresql.ARRAY(sa.String), default=[]),
        sa.Column('initialization_error', sa.Text),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending', 'initializing', 'running', 'paused', 'completed', 'error', 'cleaning_up')",
            name='valid_session_status',
        ),
    )
    op.create_index('idx_sessions_org', 'sessions', ['org_id'])
    op.create_index('idx_sessions_created_by', 'sessions', ['created_by'])
    op.create_index('idx_sessions_status', 'sessions', ['status'])
    op.create_index('idx_sessions_created', 'sessions', ['created_at'])
    op.execute(
        "CREATE INDEX idx_sessions_active ON sessions (org_id, status) WHERE status IN ('pending', 'running', 'paused')"
    )
    
    # ==================== Session Events ====================
    op.create_table(
        'session_events',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'session_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('sessions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('agent', sa.String(20), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "agent IN ('red', 'blue', 'orchestrator')",
            name='valid_agent',
        ),
    )
    op.create_index('idx_session_events_session', 'session_events', ['session_id', 'created_at'])
    op.create_index('idx_session_events_type', 'session_events', ['session_id', 'event_type'])
    
    # ==================== Findings ====================
    op.create_table(
        'findings',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'session_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('sessions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('agent', sa.String(20), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('evidence', sa.Text),
        sa.Column('recommendation', sa.Text),
        sa.Column('cve', sa.String(50)),
        sa.Column('cvss_score', sa.Numeric(3, 1)),
        sa.Column('category', sa.String(100)),
        sa.Column('tool', sa.String(100)),
        sa.Column('raw_output', sa.Text),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            'verified_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
        ),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('is_false_positive', sa.Boolean, default=False),
        sa.CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low', 'info')",
            name='valid_severity',
        ),
        sa.CheckConstraint(
            "agent IN ('red', 'blue')",
            name='valid_finding_agent',
        ),
    )
    op.create_index('idx_findings_session', 'findings', ['session_id'])
    op.create_index('idx_findings_severity', 'findings', ['session_id', 'severity'])
    op.execute(
        "CREATE INDEX idx_findings_cve ON findings (cve) WHERE cve IS NOT NULL"
    )
    
    # ==================== Agent States ====================
    op.create_table(
        'agent_states',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'session_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('sessions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('agent_type', sa.String(20), nullable=False),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('conversation_history', postgresql.JSONB, default=[]),
        sa.Column('steps', postgresql.JSONB, default=[]),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "agent_type IN ('red', 'blue')",
            name='valid_agent_type',
        ),
        sa.CheckConstraint(
            "state IN ('idle', 'running', 'paused', 'completed', 'error')",
            name='valid_agent_state',
        ),
        sa.UniqueConstraint('session_id', 'agent_type', name='uq_session_agent'),
    )
    
    # ==================== Rate Limit Bans ====================
    op.create_table(
        'rate_limit_bans',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('ip_address', sa.String(45)),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
        ),
        sa.Column('reason', sa.String(100), nullable=False),
        sa.Column('ban_type', sa.String(50), nullable=False),
        sa.Column('banned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('request_count', sa.Integer),
        sa.Column('threshold', sa.Integer),
        sa.Column('unbanned_at', sa.DateTime(timezone=True)),
        sa.Column(
            'unbanned_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
        ),
        sa.Column('unban_reason', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.CheckConstraint(
            "ban_type IN ('temporary', 'permanent')",
            name='valid_ban_type',
        ),
    )
    op.execute(
        "CREATE INDEX idx_rate_bans_ip ON rate_limit_bans (ip_address) WHERE is_active = TRUE"
    )
    op.execute(
        "CREATE INDEX idx_rate_bans_user ON rate_limit_bans (user_id) WHERE is_active = TRUE"
    )
    
    # ==================== Insert Default Data ====================
    
    # Insert default roles
    op.execute("""
        INSERT INTO roles (id, name, description, is_system) VALUES
        (uuid_generate_v4(), 'admin', 'Full system administrator', TRUE),
        (uuid_generate_v4(), 'analyst', 'Security analyst with execution rights', TRUE),
        (uuid_generate_v4(), 'viewer', 'Read-only access', TRUE),
        (uuid_generate_v4(), 'service', 'Service account for automation', TRUE)
    """)
    
    # Insert default permissions
    op.execute("""
        INSERT INTO permissions (id, name, description, category) VALUES
        -- Session permissions
        (uuid_generate_v4(), 'sessions:read', 'View session details', 'sessions'),
        (uuid_generate_v4(), 'sessions:write', 'Create and modify sessions', 'sessions'),
        (uuid_generate_v4(), 'sessions:delete', 'Delete sessions', 'sessions'),
        (uuid_generate_v4(), 'sessions:execute', 'Start, pause, resume, stop sessions', 'sessions'),
        -- Finding permissions
        (uuid_generate_v4(), 'findings:read', 'View security findings', 'findings'),
        (uuid_generate_v4(), 'findings:write', 'Create and modify findings', 'findings'),
        (uuid_generate_v4(), 'findings:export', 'Export findings to external formats', 'findings'),
        -- LLM permissions
        (uuid_generate_v4(), 'llm:configure', 'Configure LLM endpoints', 'llm'),
        (uuid_generate_v4(), 'llm:test', 'Test LLM connections', 'llm'),
        -- User management
        (uuid_generate_v4(), 'users:manage', 'Create, modify, delete users', 'users'),
        (uuid_generate_v4(), 'users:read', 'View user profiles', 'users'),
        -- Audit
        (uuid_generate_v4(), 'audit:read', 'View audit logs', 'audit'),
        -- System
        (uuid_generate_v4(), 'system:configure', 'Modify system settings', 'system')
    """)
    
    # Insert role-permission mappings for admin (all permissions)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'admin'
    """)
    
    # Insert role-permission mappings for analyst
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p 
        WHERE r.name = 'analyst' 
        AND p.name IN (
            'sessions:read', 'sessions:write', 'sessions:execute',
            'findings:read', 'findings:write', 'findings:export',
            'llm:test'
        )
    """)
    
    # Insert role-permission mappings for viewer
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p 
        WHERE r.name = 'viewer' 
        AND p.name IN ('sessions:read', 'findings:read')
    """)
    
    # Insert role-permission mappings for service
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p 
        WHERE r.name = 'service' 
        AND p.name IN (
            'sessions:read', 'sessions:write', 'sessions:execute',
            'findings:read', 'findings:write'
        )
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('rate_limit_bans')
    op.drop_table('agent_states')
    op.drop_table('findings')
    op.drop_table('session_events')
    op.drop_table('sessions')
    op.drop_table('audit_log')
    op.drop_table('login_history')
    op.drop_table('api_keys')
    op.drop_table('refresh_tokens')
    op.drop_table('authorized_targets')
    op.drop_table('organization_members')
    op.drop_table('organizations')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('users')
    op.drop_table('permissions')
    op.drop_table('roles')
    
    # Drop extension
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')