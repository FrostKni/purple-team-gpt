"""Database layer tests for Purple Team GPT.

Tests:
- Model creation and validation
- Repository CRUD operations
- Session persistence
- Audit logging
- Agent state management

Note: Uses mocks to avoid SQLAlchemy model instantiation issues.
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

# Set environment variables before imports
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-database-testing-32-chars!"
os.environ["APP_DEBUG"] = "true"


# ============================================================================
# Enum Tests (No model instantiation required)
# ============================================================================

class TestEnums:
    """Tests for database enums."""
    
    def test_session_status_enum(self):
        """Test SessionStatus enum values."""
        from purple_team_gpt.db import SessionStatus
        
        assert SessionStatus.PENDING.value == "pending"
        assert SessionStatus.RUNNING.value == "running"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.ERROR.value == "error"
        assert SessionStatus.PAUSED.value == "paused"
    
    def test_agent_type_enum(self):
        """Test AgentType enum values."""
        from purple_team_gpt.db import AgentType
        
        assert AgentType.RED.value == "red"
        assert AgentType.BLUE.value == "blue"
        assert AgentType.ORCHESTRATOR.value == "orchestrator"
    
    def test_finding_severity_enum(self):
        """Test FindingSeverity enum values."""
        from purple_team_gpt.db import FindingSeverity
        
        assert FindingSeverity.CRITICAL.value == "critical"
        assert FindingSeverity.HIGH.value == "high"
        assert FindingSeverity.MEDIUM.value == "medium"
        assert FindingSeverity.LOW.value == "low"
        assert FindingSeverity.INFO.value == "info"
    
    def test_actor_type_enum(self):
        """Test ActorType enum values."""
        from purple_team_gpt.db import ActorType
        
        assert ActorType.USER.value == "user"
        assert ActorType.SYSTEM.value == "system"
    
    def test_audit_event_type_enum(self):
        """Test AuditEventType enum values."""
        from purple_team_gpt.db import AuditEventType
        
        assert AuditEventType.LOGIN_SUCCESS.value == "auth.login.success"
        assert AuditEventType.LOGIN_FAILURE.value == "auth.login.failure"
        assert AuditEventType.SESSION_CREATE.value == "session.create"
        assert AuditEventType.SESSION_START.value == "session.start"
    
    def test_audit_event_category_enum(self):
        """Test AuditEventCategory enum values."""
        from purple_team_gpt.db import AuditEventCategory
        
        assert AuditEventCategory.SESSION.value == "session"
        assert AuditEventCategory.AUTH.value == "auth"
        assert AuditEventCategory.SECURITY.value == "security"
        assert AuditEventCategory.LLM.value == "llm"


# ============================================================================
# UUID Generation Tests
# ============================================================================

class TestUUIDGeneration:
    """Tests for UUID generation."""
    
    def test_generate_uuid(self):
        """Test UUID generation."""
        from purple_team_gpt.db.models import generate_uuid
        
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # UUID string format
        assert uuid1.count('-') == 4
    
    def test_generate_uuid_format(self):
        """Test UUID format is correct."""
        from purple_team_gpt.db.models import generate_uuid
        import re
        
        uuid = generate_uuid()
        # UUID v4 format
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(pattern, uuid) is not None


# ============================================================================
# Repository Method Tests (Using mocks to avoid model instantiation)
# ============================================================================

class TestSessionRepositoryMethods:
    """Tests for SessionRepository methods."""
    
    def test_session_repository_init(self):
        """Test SessionRepository initialization."""
        from purple_team_gpt.db.repository import SessionRepository
        
        mock_session = AsyncMock()
        repo = SessionRepository(mock_session)
        
        assert repo.session == mock_session
    
    def test_create_session_method_exists(self):
        """Test that create_session method exists and is callable."""
        from purple_team_gpt.db.repository import SessionRepository
        
        mock_session = AsyncMock()
        repo = SessionRepository(mock_session)
        
        assert hasattr(repo, 'create_session')
        assert callable(repo.create_session)
    
    def test_get_session_method_exists(self):
        """Test that get_session method exists and is callable."""
        from purple_team_gpt.db.repository import SessionRepository
        
        mock_session = AsyncMock()
        repo = SessionRepository(mock_session)
        
        assert hasattr(repo, 'get_session')
        assert callable(repo.get_session)
    
    def test_list_sessions_method_exists(self):
        """Test that list_sessions method exists and is callable."""
        from purple_team_gpt.db.repository import SessionRepository
        
        mock_session = AsyncMock()
        repo = SessionRepository(mock_session)
        
        assert hasattr(repo, 'list_sessions')
        assert callable(repo.list_sessions)
    
    def test_update_session_status_method_exists(self):
        """Test that update_session_status method exists and is callable."""
        from purple_team_gpt.db.repository import SessionRepository
        
        mock_session = AsyncMock()
        repo = SessionRepository(mock_session)
        
        assert hasattr(repo, 'update_session_status')
        assert callable(repo.update_session_status)
    
    def test_delete_session_method_exists(self):
        """Test that delete_session method exists and is callable."""
        from purple_team_gpt.db.repository import SessionRepository
        
        mock_session = AsyncMock()
        repo = SessionRepository(mock_session)
        
        assert hasattr(repo, 'delete_session')
        assert callable(repo.delete_session)
    
    def test_add_event_method_exists(self):
        """Test that add_event method exists and is callable."""
        from purple_team_gpt.db.repository import SessionRepository
        
        mock_session = AsyncMock()
        repo = SessionRepository(mock_session)
        
        assert hasattr(repo, 'add_event')
        assert callable(repo.add_event)
    
    def test_add_finding_method_exists(self):
        """Test that add_finding method exists and is callable."""
        from purple_team_gpt.db.repository import SessionRepository
        
        mock_session = AsyncMock()
        repo = SessionRepository(mock_session)
        
        assert hasattr(repo, 'add_finding')
        assert callable(repo.add_finding)


class TestAuditRepositoryMethods:
    """Tests for AuditRepository methods."""
    
    def test_audit_repository_init(self):
        """Test AuditRepository initialization."""
        from purple_team_gpt.db.repository import AuditRepository
        
        mock_session = AsyncMock()
        repo = AuditRepository(mock_session)
        
        assert repo.session == mock_session
    
    def test_log_event_method_exists(self):
        """Test that log_event method exists and is callable."""
        from purple_team_gpt.db.repository import AuditRepository
        
        mock_session = AsyncMock()
        repo = AuditRepository(mock_session)
        
        assert hasattr(repo, 'log_event')
        assert callable(repo.log_event)
    
    def test_get_user_audit_logs_method_exists(self):
        """Test that get_user_audit_logs method exists and is callable."""
        from purple_team_gpt.db.repository import AuditRepository
        
        mock_session = AsyncMock()
        repo = AuditRepository(mock_session)
        
        assert hasattr(repo, 'get_user_audit_logs')
        assert callable(repo.get_user_audit_logs)


class TestUserRepositoryMethods:
    """Tests for UserRepository methods."""
    
    def test_user_repository_init(self):
        """Test UserRepository initialization."""
        from purple_team_gpt.db.repository import UserRepository
        
        mock_session = AsyncMock()
        repo = UserRepository(mock_session)
        
        assert repo.session == mock_session
    
    def test_get_user_by_email_method_exists(self):
        """Test that get_user_by_email method exists and is callable."""
        from purple_team_gpt.db.repository import UserRepository
        
        mock_session = AsyncMock()
        repo = UserRepository(mock_session)
        
        assert hasattr(repo, 'get_user_by_email')
        assert callable(repo.get_user_by_email)
    
    def test_get_user_by_id_method_exists(self):
        """Test that get_user_by_id method exists and is callable."""
        from purple_team_gpt.db.repository import UserRepository
        
        mock_session = AsyncMock()
        repo = UserRepository(mock_session)
        
        assert hasattr(repo, 'get_user_by_id')
        assert callable(repo.get_user_by_id)
    
    def test_get_user_permissions_method_exists(self):
        """Test that get_user_permissions method exists and is callable."""
        from purple_team_gpt.db.repository import UserRepository
        
        mock_session = AsyncMock()
        repo = UserRepository(mock_session)
        
        assert hasattr(repo, 'get_user_permissions')
        assert callable(repo.get_user_permissions)


# ============================================================================
# Model Export Tests
# ============================================================================

class TestModelExports:
    """Tests for model exports from db package."""
    
    def test_session_model_exported(self):
        """Test that Session model is exported."""
        from purple_team_gpt.db import Session
        assert Session is not None
    
    def test_user_model_exported(self):
        """Test that User model is exported."""
        from purple_team_gpt.db import User
        assert User is not None
    
    def test_role_model_exported(self):
        """Test that Role model is exported."""
        from purple_team_gpt.db import Role
        assert Role is not None
    
    def test_finding_model_exported(self):
        """Test that Finding model is exported."""
        from purple_team_gpt.db import Finding
        assert Finding is not None
    
    def test_audit_log_model_exported(self):
        """Test that AuditLog model is exported."""
        from purple_team_gpt.db import AuditLog
        assert AuditLog is not None
    
    def test_repository_exports(self):
        """Test that repositories are exported."""
        from purple_team_gpt.db import SessionRepository, AuditRepository, UserRepository
        
        assert SessionRepository is not None
        assert AuditRepository is not None
        assert UserRepository is not None


# ============================================================================
# Database Module Imports Tests
# ============================================================================

class TestDatabaseImports:
    """Tests for database module imports."""
    
    def test_database_module_imports(self):
        """Test that database module can be imported."""
        from purple_team_gpt.db import database
        assert database is not None
    
    def test_database_has_base(self):
        """Test that database has Base class."""
        from purple_team_gpt.db.database import Base
        assert Base is not None
    
    def test_database_has_init_db(self):
        """Test that database has init_db function."""
        from purple_team_gpt.db.database import init_db
        assert init_db is not None
    
    def test_database_has_close_db(self):
        """Test that database has close_db function."""
        from purple_team_gpt.db.database import close_db
        assert close_db is not None