"""Database repository pattern for session management.

This module provides async repository classes for database operations,
abstracting SQLAlchemy session management from business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from purple_team_gpt.db.models import (
    Session as SessionModel,
    SessionEvent,
    Finding,
    AgentState,
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    Organization,
    AuditLog,
    SessionStatus,
    AgentType,
    FindingSeverity,
    AuditEventType,
    AuditEventCategory,
)

logger = logging.getLogger(__name__)


try:
    from purple_team_gpt.agents.base import Finding as AgentFinding
except ImportError:
    AgentFinding = None  # type: ignore


class SessionRepository:
    """Repository for session database operations.

    Provides async CRUD operations for sessions, events, and findings.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create_session(
        self,
        target: str,
        scope: str = "",
        org_id: Optional[str] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> SessionModel:
        """Create a new session.

        Args:
            target: Target system/network for assessment.
            scope: Scope restrictions and constraints.
            org_id: Organization ID for multi-tenancy.
            created_by: User ID who created the session.
            metadata: Additional session metadata.
            tags: Session tags.

        Returns:
            Created Session model instance.
        """
        session = SessionModel(
            target=target,
            scope=scope,
            org_id=org_id,
            created_by=created_by,
            status=SessionStatus.PENDING.value,
            session_metadata=metadata or {},
            tags=tags or [],
        )
        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)
        logger.info(f"Created session {session.id} for target {target}")
        return session

    async def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get a session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            Session model or None if not found.
        """
        result = await self.session.execute(
            select(SessionModel)
            .options(selectinload(SessionModel.events), selectinload(SessionModel.findings))
            .where(SessionModel.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SessionModel]:
        """List sessions with optional filters.

        Args:
            org_id: Filter by organization.
            status: Filter by status.
            created_by: Filter by creator.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            List of Session models.
        """
        query = select(SessionModel)

        conditions = []
        if org_id:
            conditions.append(SessionModel.org_id == org_id)
        if status:
            conditions.append(SessionModel.status == status)
        if created_by:
            conditions.append(SessionModel.created_by == created_by)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(SessionModel.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[SessionModel]:
        """Update session status.

        Args:
            session_id: Session identifier.
            status: New status value.
            started_at: When session started.
            completed_at: When session completed.

        Returns:
            Updated Session model or None.
        """
        update_data = {
            "status": status,
            "last_activity_at": datetime.utcnow(),
        }
        if started_at is not None:
            update_data["started_at"] = started_at
        if completed_at is not None:
            update_data["completed_at"] = completed_at

        await self.session.execute(
            update(SessionModel).where(SessionModel.id == session_id).values(**update_data)
        )
        return await self.get_session(session_id)

    async def update_session_metrics(
        self,
        session_id: str,
        red_findings_count: Optional[int] = None,
        blue_findings_count: Optional[int] = None,
        critical_findings_count: Optional[int] = None,
        high_findings_count: Optional[int] = None,
        total_steps: Optional[int] = None,
        total_events: Optional[int] = None,
    ) -> None:
        """Update session metrics.

        Args:
            session_id: Session identifier.
            red_findings_count: Count of red agent findings.
            blue_findings_count: Count of blue agent findings.
            critical_findings_count: Count of critical findings.
            high_findings_count: Count of high findings.
            total_steps: Total steps taken.
            total_events: Total events recorded.
        """
        update_data = {"last_activity_at": datetime.utcnow()}

        if red_findings_count is not None:
            update_data["red_findings_count"] = red_findings_count
        if blue_findings_count is not None:
            update_data["blue_findings_count"] = blue_findings_count
        if critical_findings_count is not None:
            update_data["critical_findings_count"] = critical_findings_count
        if high_findings_count is not None:
            update_data["high_findings_count"] = high_findings_count
        if total_steps is not None:
            update_data["total_steps"] = total_steps
        if total_events is not None:
            update_data["total_events"] = total_events

        await self.session.execute(
            update(SessionModel).where(SessionModel.id == session_id).values(**update_data)
        )

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data.

        Args:
            session_id: Session identifier.

        Returns:
            True if deleted, False if not found.
        """
        result = await self.session.execute(
            delete(SessionModel).where(SessionModel.id == session_id)
        )
        return result.rowcount > 0

    # ==================== Session Events ====================

    async def add_event(
        self,
        session_id: str,
        agent: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> SessionEvent:
        """Add an event to a session.

        Args:
            session_id: Session identifier.
            agent: Agent that emitted the event.
            event_type: Type of event.
            data: Event data.

        Returns:
            Created SessionEvent instance.
        """
        event = SessionEvent(
            session_id=session_id,
            agent=agent,
            event_type=event_type,
            data=data,
        )
        self.session.add(event)

        # Update session event count
        await self.session.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(
                total_events=SessionModel.total_events + 1,
                last_activity_at=datetime.utcnow(),
            )
        )

        await self.session.flush()
        return event

    async def get_events(
        self,
        session_id: str,
        agent: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[SessionEvent]:
        """Get events for a session.

        Args:
            session_id: Session identifier.
            agent: Filter by agent.
            event_type: Filter by event type.
            limit: Maximum results.

        Returns:
            List of SessionEvent instances.
        """
        query = select(SessionEvent).where(SessionEvent.session_id == session_id)

        if agent:
            query = query.where(SessionEvent.agent == agent)
        if event_type:
            query = query.where(SessionEvent.event_type == event_type)

        query = query.order_by(SessionEvent.created_at).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==================== Findings ====================

    async def add_finding(
        self,
        session_id: str,
        agent_or_finding: Any,
        title: Optional[str] = None,
        severity: Optional[str] = None,
        description: Optional[str] = None,
        evidence: Optional[str] = None,
        recommendation: Optional[str] = None,
        cve: Optional[str] = None,
        cvss_score: Optional[float] = None,
        category: Optional[str] = None,
        tool: Optional[str] = None,
        raw_output: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Finding:
        """Add a finding to a session.

        Can be called in two ways:
        1. With a Finding object: add_finding(session_id, finding, agent_name)
        2. With individual parameters: add_finding(session_id, agent, title, severity, ...)

        Args:
            session_id: Session identifier.
            agent_or_finding: Either the agent name (str) or a Finding object from agents/base.py.
            title: Finding title (required if agent_or_finding is a string).
            severity: Severity level (required if agent_or_finding is a string).
            description: Finding description.
            evidence: Evidence found.
            recommendation: Remediation recommendation.
            cve: CVE identifier if applicable.
            cvss_score: CVSS score.
            category: Finding category.
            tool: Tool used to find the issue.
            raw_output: Raw tool output.
            metadata: Additional metadata.

        Returns:
            Created Finding instance.
        """
        # Check if agent_or_finding is a Finding object from agents/base.py
        if isinstance(agent_or_finding, str):
            # It's the agent string - use individual parameters
            agent = agent_or_finding
        else:
            # It's a Finding object - extract fields
            finding_obj = agent_or_finding
            agent = title if title else "unknown"
            title = finding_obj.title
            severity = finding_obj.severity
            description = finding_obj.description
            evidence = finding_obj.evidence
            recommendation = finding_obj.recommendation
            cve = finding_obj.cve
            cvss_score = float(finding_obj.cvss_score) if finding_obj.cvss_score else None
            tool = finding_obj.tool
        finding = Finding(
            session_id=session_id,
            agent=agent,
            title=title,
            severity=severity,
            description=description,
            evidence=evidence,
            recommendation=recommendation,
            cve=cve,
            cvss_score=cvss_score,
            category=category,
            tool=tool,
            raw_output=raw_output,
            finding_metadata=metadata or {},
        )
        self.session.add(finding)

        # Update session finding counts
        update_data = {"last_activity_at": datetime.utcnow()}
        if agent == "red":
            update_data["red_findings_count"] = SessionModel.red_findings_count + 1
        elif agent == "blue":
            update_data["blue_findings_count"] = SessionModel.blue_findings_count + 1

        if severity == "critical":
            update_data["critical_findings_count"] = SessionModel.critical_findings_count + 1
        elif severity == "high":
            update_data["high_findings_count"] = SessionModel.high_findings_count + 1

        await self.session.execute(
            update(SessionModel).where(SessionModel.id == session_id).values(**update_data)
        )

        await self.session.flush()
        return finding

    async def get_findings(
        self,
        session_id: str,
        agent: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Finding]:
        """Get findings for a session.

        Args:
            session_id: Session identifier.
            agent: Filter by agent.
            severity: Filter by severity.
            limit: Maximum results.

        Returns:
            List of Finding instances.
        """
        query = select(Finding).where(Finding.session_id == session_id)

        if agent:
            query = query.where(Finding.agent == agent)
        if severity:
            query = query.where(Finding.severity == severity)

        query = query.order_by(Finding.created_at).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==================== Agent State ====================

    async def save_agent_state(
        self,
        session_id: str,
        agent_type: str,
        state: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentState:
        """Save or update agent state.

        Args:
            session_id: Session identifier.
            agent_type: Type of agent (red/blue).
            state: Agent state.
            conversation_history: Conversation history.
            steps: Step history.

        Returns:
            Created or updated AgentState instance.
        """
        # Check if state exists
        result = await self.session.execute(
            select(AgentState).where(
                and_(
                    AgentState.session_id == session_id,
                    AgentState.agent_type == agent_type,
                )
            )
        )
        agent_state = result.scalar_one_or_none()

        if agent_state:
            # Update existing
            agent_state.state = state
            if conversation_history is not None:
                agent_state.conversation_history = conversation_history
            if steps is not None:
                agent_state.steps = steps
            agent_state.updated_at = datetime.utcnow()
        else:
            # Create new
            agent_state = AgentState(
                session_id=session_id,
                agent_type=agent_type,
                state=state,
                conversation_history=conversation_history or [],
                steps=steps or [],
            )
            self.session.add(agent_state)

        await self.session.flush()
        return agent_state

    async def get_agent_state(
        self,
        session_id: str,
        agent_type: str,
    ) -> Optional[AgentState]:
        """Get agent state.

        Args:
            session_id: Session identifier.
            agent_type: Type of agent (red/blue).

        Returns:
            AgentState instance or None.
        """
        result = await self.session.execute(
            select(AgentState).where(
                and_(
                    AgentState.session_id == session_id,
                    AgentState.agent_type == agent_type,
                )
            )
        )
        return result.scalar_one_or_none()


class AuditRepository:
    """Repository for audit log operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def log_event(
        self,
        event_type: str,
        event_category: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        actor_type: str = "user",
        actor_ip: Optional[str] = None,
        actor_user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            event_type: Type of event.
            event_category: Category of event.
            user_id: User who triggered the event.
            org_id: Organization context.
            actor_type: Type of actor (user/system/api_key).
            actor_ip: IP address of actor.
            actor_user_agent: User agent of actor.
            resource_type: Type of resource affected.
            resource_id: ID of resource affected.
            resource_action: Action taken on resource.
            details: Additional event details.
            request_id: Request ID for tracing.
            request_method: HTTP method.
            request_path: HTTP path.
            success: Whether the event succeeded.
            error_message: Error message if failed.

        Returns:
            Created AuditLog instance.
        """
        audit_log = AuditLog(
            event_type=event_type,
            event_category=event_category,
            user_id=user_id,
            org_id=org_id,
            actor_type=actor_type,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_action=resource_action,
            details=details or {},
            request_id=request_id,
            request_method=request_method,
            request_path=request_path,
            success=success,
            error_message=error_message,
        )
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log

    async def get_user_audit_logs(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Get audit logs for a user.

        Args:
            user_id: User identifier.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            List of AuditLog instances.
        """
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class UserRepository:
    """Repository for user operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email.

        Args:
            email: User email.

        Returns:
            User instance or None.
        """
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: User identifier.

        Returns:
            User instance or None.
        """
        result = await self.session.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user.

        Args:
            user_id: User identifier.

        Returns:
            List of permission names.
        """
        result = await self.session.execute(
            select(Permission.name)
            .distinct()
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(UserRole, RolePermission.role_id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        return [row[0] for row in result.all()]


__all__ = [
    "SessionRepository",
    "AuditRepository",
    "UserRepository",
]
