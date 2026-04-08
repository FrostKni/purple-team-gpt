"""Purple Orchestrator - Coordinates Red and Blue agents in real-time.

This module implements the orchestrator that manages simultaneous execution
of Red (offensive) and Blue (defensive) agents, with event routing between
them for real-time purple team exercises.
"""

import asyncio
import functools
import logging
import uuid
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from purple_team_gpt.agents.base import AgentStateEnum, Finding
from purple_team_gpt.agents.red_agent import RedAgent
from purple_team_gpt.agents.blue_agent import BlueAgent
from purple_team_gpt.core.llm.engine import LLMEngine
from purple_team_gpt.core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


# Session cleanup settings
SESSION_IDLE_TIMEOUT_MINUTES = 60
SESSION_CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes
MAX_SESSIONS = 100


class SimulationStatus(str, Enum):
    """Status of a simulation session."""

    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CLEANING_UP = "cleaning_up"


@dataclass
class SimulationSession:
    """A simulation session containing Red and Blue agent activities.

    Attributes:
        id: Unique session identifier
        target: Target system/network for assessment
        scope: Scope restrictions and constraints
        status: Current session status
        created_at: Session creation timestamp
        started_at: Session start timestamp
        completed_at: Session completion timestamp
        last_activity_at: Last activity timestamp (for cleanup)
        red_findings: Findings from Red Agent
        blue_findings: Findings from Blue Agent
        events: Chronological list of all events
        metadata: Additional session metadata
        initialization_error: Error during initialization if any
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: str = ""
    scope: str = ""
    status: SimulationStatus = SimulationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity_at: datetime = field(default_factory=datetime.utcnow)
    red_findings: List[Finding] = field(default_factory=list)
    blue_findings: List[Finding] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    initialization_error: Optional[str] = None

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = datetime.utcnow()

    def is_idle(self, timeout_minutes: int = SESSION_IDLE_TIMEOUT_MINUTES) -> bool:
        """Check if session has been idle too long."""
        if self.status in (SimulationStatus.COMPLETED, SimulationStatus.ERROR):
            return True
        idle_time = datetime.utcnow() - self.last_activity_at
        return idle_time > timedelta(minutes=timeout_minutes)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            "id": self.id,
            "target": self.target,
            "scope": self.scope,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_activity_at": self.last_activity_at.isoformat()
            if self.last_activity_at
            else None,
            "red_findings_count": len(self.red_findings),
            "blue_findings_count": len(self.blue_findings),
            "events_count": len(self.events),
            "initialization_error": self.initialization_error,
        }


@dataclass
class AgentEvent:
    """Event emitted by an agent during execution.

    Events are used for inter-agent communication and real-time
    monitoring of session progress.

    Attributes:
        session_id: ID of the session this event belongs to
        agent: Agent that emitted the event ("red" or "blue")
        event_type: Type of event (step, finding, response, error, etc.)
        data: Event payload data
        timestamp: When the event occurred
    """

    session_id: str
    agent: str  # "red" or "blue"
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "session_id": self.session_id,
            "agent": self.agent,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class PurpleOrchestrator:
    """Coordinates Red and Blue agents in real-time.

    The Purple Orchestrator manages simultaneous execution of offensive
    (Red) and defensive (Blue) security agents, enabling real-time
    purple team exercises with event-based communication.

    Features:
    - Concurrent agent execution via asyncio.gather
    - Event routing between agents via asyncio.Queue
    - Session lifecycle management
    - Real-time event callbacks for UI integration
    - Metrics collection and reporting
    - Automatic session cleanup for idle sessions
    - Safe initialization with rollback on failure
    - PostgreSQL persistence for session data

    Example:
        orchestrator = PurpleOrchestrator(engine, vector_store)
        session = orchestrator.create_session("192.168.1.1", "Authorized test")
        await orchestrator.start_session(session.id)
        metrics = orchestrator.get_metrics(session.id)
    """

    def __init__(
        self,
        engine: LLMEngine,
        vector_store: VectorStore,
        session_repository: Optional[Any] = None,
        on_event: Optional[Callable[[AgentEvent], None]] = None,
        max_steps: int = 50,
        safe_mode: bool = True,
        enable_cleanup: bool = True,
    ):
        """Initialize the Purple Orchestrator.

        Args:
            engine: LLM engine for agent conversations
            vector_store: Vector store for RAG queries
            session_repository: Database session factory for persistence (e.g., get_session).
                               Pass None to disable database persistence.
            on_event: Callback for real-time event notifications
            max_steps: Maximum steps per agent per session
            safe_mode: Enable safe mode for tool execution
            enable_cleanup: Enable automatic session cleanup
        """
        self.engine = engine
        self.vector_store = vector_store
        self.session_repository = session_repository
        self.on_event = on_event
        self.max_steps = max_steps
        self.safe_mode = safe_mode
        self._enable_cleanup = enable_cleanup
        self.use_database = session_repository is not None

        # Session management (in-memory for active sessions)
        self.sessions: Dict[str, SimulationSession] = {}
        self.red_agents: Dict[str, RedAgent] = {}
        self.blue_agents: Dict[str, BlueAgent] = {}

        # Event routing
        self._event_queues: Dict[str, asyncio.Queue] = {}

        # Background tasks tracking
        self._session_tasks: Dict[str, asyncio.Task] = {}

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Track initialized sessions for rollback
        self._initialized_sessions: Set[str] = set()

        # Start cleanup task if enabled
        if self._enable_cleanup:
            self._start_cleanup_task()

        logger.info(
            f"Purple Orchestrator initialized (database={'enabled' if self.use_database else 'disabled'})"
        )

    async def _persist_session(self, session: SimulationSession) -> None:
        """Persist session to database if enabled.

        Args:
            session: Session to persist
        """
        if not self.session_repository:
            return

        try:
            from purple_team_gpt.db.repository import SessionRepository

            async with self.session_repository() as db_session:
                repo = SessionRepository(db_session)

                # Check if session exists
                existing = await repo.get_session(session.id)
                if existing:
                    # Update existing session
                    await repo.update_session_status(
                        session.id,
                        session.status,
                        session.started_at,
                        session.completed_at,
                    )
                else:
                    # Create new session
                    await repo.create_session(
                        target=session.target,
                        scope=session.scope,
                        metadata=session.metadata,
                    )
        except Exception as e:
            logger.error(f"Failed to persist session {session.id}: {e}")

    async def _persist_finding(self, session_id: str, agent: str, finding: Finding) -> None:
        """Persist finding to database if enabled.

        Args:
            session_id: Session identifier
            agent: Agent that found the issue
            finding: Finding to persist
        """
        if not self.session_repository:
            return

        try:
            from purple_team_gpt.db.repository import SessionRepository

            async with self.session_repository() as db_session:
                repo = SessionRepository(db_session)
                await repo.add_finding(session_id, agent, finding)
        except Exception as e:
            logger.error(f"Failed to persist finding: {e}")

    async def _persist_event(
        self,
        session_id: str,
        agent: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Persist event to database if enabled.

        Args:
            session_id: Session identifier
            agent: Agent that emitted the event
            event_type: Type of event
            data: Event payload
        """
        if not self.session_repository:
            return

        try:
            from purple_team_gpt.db.repository import SessionRepository

            async with self.session_repository() as db_session:
                repo = SessionRepository(db_session)
                await repo.add_event(session_id, agent, event_type, data)
        except Exception as e:
            logger.error(f"Failed to persist event: {e}")

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.debug("Session cleanup task started")
        except RuntimeError:
            # No running loop - will start on first async operation
            logger.debug("No running loop, cleanup will start on first operation")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up idle sessions."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(SESSION_CLEANUP_INTERVAL_SECONDS)
                await self._cleanup_idle_sessions()
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_idle_sessions(self) -> int:
        """Clean up sessions that have been idle too long.

        Returns:
            Number of sessions cleaned up
        """
        cleaned = 0
        sessions_to_clean = []

        for session_id, session in list(self.sessions.items()):
            if session.is_idle(SESSION_IDLE_TIMEOUT_MINUTES):
                sessions_to_clean.append(session_id)

        for session_id in sessions_to_clean:
            try:
                logger.info(f"Cleaning up idle session: {session_id}")
                self.delete_session(session_id)
                cleaned += 1
            except Exception as e:
                logger.error(f"Failed to cleanup session {session_id}: {e}")

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} idle sessions")

        return cleaned

    def _check_session_limit(self) -> None:
        """Check if we've reached the session limit.

        Raises:
            RuntimeError: If session limit reached
        """
        active_count = sum(
            1
            for s in self.sessions.values()
            if s.status
            in (SimulationStatus.RUNNING, SimulationStatus.PAUSED, SimulationStatus.PENDING)
        )
        if active_count >= MAX_SESSIONS:
            raise RuntimeError(
                f"Maximum session limit ({MAX_SESSIONS}) reached. "
                "Please clean up existing sessions."
            )

    def create_session(
        self,
        target: str,
        scope: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SimulationSession:
        """Create a new simulation session.

        Creates a session and initializes Red and Blue agents for
        the specified target. The session starts in PENDING status.

        Args:
            target: Target system/network for assessment
            scope: Scope restrictions and constraints
            metadata: Additional session metadata

        Returns:
            Created SimulationSession object

        Raises:
            RuntimeError: If session limit reached
        """
        # Check session limit
        self._check_session_limit()

        session = SimulationSession(
            target=target,
            scope=scope,
            metadata=metadata or {},
        )

        # Persist to database if enabled (fire and forget)
        if self.use_database:
            asyncio.create_task(self._persist_session_create(session))

        # Start with session in dict so we can track partial init
        self.sessions[session.id] = session
        self._event_queues[session.id] = asyncio.Queue(maxsize=500)

        try:
            # Create Red Agent with callbacks
            self.red_agents[session.id] = RedAgent(
                engine=self.engine,
                vector_store=self.vector_store,
                on_step=functools.partial(self._handle_step, session.id, "red"),
                on_finding=functools.partial(self._handle_finding, session.id, "red"),
                on_output=functools.partial(self._handle_output, session.id, "red"),
                max_steps=self.max_steps,
                safe_mode=self.safe_mode,
            )

            # Create Blue Agent with callbacks
            self.blue_agents[session.id] = BlueAgent(
                engine=self.engine,
                vector_store=self.vector_store,
                on_step=functools.partial(self._handle_step, session.id, "blue"),
                on_finding=functools.partial(self._handle_finding, session.id, "blue"),
                on_output=functools.partial(self._handle_output, session.id, "blue"),
                max_steps=self.max_steps,
                safe_mode=self.safe_mode,
                monitored_system=target,
            )

            self._initialized_sessions.add(session.id)

        except Exception as e:
            # Rollback partial initialization
            logger.error(f"Failed to initialize session {session.id}: {e}")
            session.initialization_error = str(e)
            session.status = SimulationStatus.ERROR
            self._cleanup_partial_session(session.id)
            raise RuntimeError(f"Failed to create session: {e}") from e

        logger.info(f"Created session {session.id} for target {target}")
        return session

    async def _persist_session_create(self, session: SimulationSession) -> None:
        """Persist session creation to database with proper error handling.

        Args:
            session: SimulationSession to persist

        Note:
            This method creates a database record for the session. If the database
            is unavailable, the session continues in-memory and this operation
            fails silently (logged but not raised).
        """
        if not self.session_repository:
            logger.debug("No database repository configured, skipping persistence")
            return

        try:
            from purple_team_gpt.db.repository import SessionRepository
            from purple_team_gpt.db.models import Session as SessionModel

            async with self.session_repository() as db_session:
                # Create session model with the same ID
                session_model = SessionModel(
                    id=session.id,
                    target=session.target,
                    scope=session.scope or "",
                    status=session.status.value,
                    session_metadata=session.metadata,
                )
                db_session.add(session_model)
                # The context manager will commit on success
            logger.info(f"Session {session.id} persisted to database")
        except Exception as e:
            logger.error(f"Failed to persist session creation: {e}")
            # Session continues in-memory, database sync can retry later
            # This is intentional - we don't want to fail the session creation
            # just because the database is unavailable

    def _cleanup_partial_session(self, session_id: str) -> None:
        """Clean up a partially initialized session."""
        # Remove agents if created
        if session_id in self.red_agents:
            try:
                self.red_agents[session_id].stop()
            except Exception:
                pass
            del self.red_agents[session_id]

        if session_id in self.blue_agents:
            try:
                self.blue_agents[session_id].stop()
            except Exception:
                pass
            del self.blue_agents[session_id]

        # Remove queue
        if session_id in self._event_queues:
            del self._event_queues[session_id]

        # Remove from initialized set
        self._initialized_sessions.discard(session_id)

    def get_session(self, session_id: str) -> Optional[SimulationSession]:
        """Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session object or None if not found
        """
        return self.sessions.get(session_id)

    def list_sessions(
        self,
        status: Optional[SimulationStatus] = None,
    ) -> List[SimulationSession]:
        """List sessions, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of Session objects
        """
        sessions = list(self.sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    async def start_session(self, session_id: str) -> None:
        """Start the simulation with both agents running simultaneously.

        Initializes both agents and runs them concurrently using
        asyncio.gather. Events are routed between agents via the
        event queue for real-time coordination.

        Args:
            session_id: Session identifier

        Raises:
            ValueError: If session not found
            RuntimeError: If session not properly initialized
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Check if session was properly initialized
        if session_id not in self._initialized_sessions:
            raise RuntimeError(f"Session {session_id} not properly initialized")

        if session.status == SimulationStatus.RUNNING:
            logger.warning(f"Session {session_id} already running")
            return

        # Update status to initializing
        session.status = SimulationStatus.INITIALIZING
        session.update_activity()

        # Initialize agents
        try:
            red_agent = self.red_agents.get(session_id)
            blue_agent = self.blue_agents.get(session_id)

            if not red_agent or not blue_agent:
                raise RuntimeError(f"Agents not found for session {session_id}")

            red_agent.initialize(session.target, session.scope)
            blue_agent.initialize(session.target, session.scope)
        except Exception as e:
            logger.error(f"Failed to initialize agents for session {session_id}: {e}")
            session.status = SimulationStatus.ERROR
            session.initialization_error = f"Agent initialization failed: {e}"
            await self._emit_event(
                session_id,
                "orchestrator",
                "initialization_error",
                {
                    "error": str(e),
                },
            )
            raise

        session.status = SimulationStatus.RUNNING
        session.started_at = datetime.utcnow()
        session.update_activity()

        # Emit session started event
        await self._emit_event(
            session_id,
            "orchestrator",
            "session_started",
            {
                "target": session.target,
                "scope": session.scope,
            },
        )

        logger.info(f"Starting session {session_id} for target {session.target}")

        try:
            # Run both agents simultaneously
            results = await asyncio.gather(
                self._run_red_agent(session_id),
                self._run_blue_agent(session_id),
                return_exceptions=True,
            )
            # Check if any agent raised an exception
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    agent_name = "red" if i == 0 else "blue"
                    logger.error(f"{agent_name} agent failed in session {session_id}: {result}")
                    # Don't re-raise - let the other agent finish gracefully
                    await self._emit_event(
                        session_id,
                        agent_name,
                        "agent_error",
                        {
                            "error": str(result),
                        },
                    )
        except asyncio.CancelledError:
            logger.info(f"Session {session_id} cancelled")
            session.status = SimulationStatus.ERROR
            await self._emit_event(session_id, "orchestrator", "session_cancelled", {})
            raise
        except Exception as e:
            logger.error(f"Session {session_id} error: {e}")
            session.status = SimulationStatus.ERROR
            await self._emit_event(
                session_id,
                "orchestrator",
                "session_error",
                {
                    "error": str(e),
                },
            )
            raise

        # Mark completed if not already
        if session.status == SimulationStatus.RUNNING:
            session.status = SimulationStatus.COMPLETED
            session.completed_at = datetime.utcnow()
            await self._emit_event(
                session_id,
                "orchestrator",
                "session_completed",
                {
                    "red_findings": len(session.red_findings),
                    "blue_findings": len(session.blue_findings),
                },
            )

        logger.info(f"Session {session_id} completed with status {session.status.value}")

    def start_session_background(self, session_id: str) -> asyncio.Task:
        """Start a session in the background.

        Creates an asyncio task for the session, allowing it to run
        without blocking the caller. Adds error handling to prevent
        unhandled exceptions.

        Args:
            session_id: Session identifier

        Returns:
            asyncio.Task for the session

        Raises:
            ValueError: If session not found
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        if session_id in self._session_tasks:
            task = self._session_tasks[session_id]
            if not task.done():
                logger.warning(f"Session {session_id} already running as background task")
                return task

        async def run_with_error_handling():
            try:
                await self.start_session(session_id)
            except Exception as e:
                logger.error(f"Background session {session_id} failed: {e}")
                # Session status already set by start_session
                raise

        task = asyncio.create_task(run_with_error_handling())
        self._session_tasks[session_id] = task

        # Add done callback for cleanup
        def on_task_done(t: asyncio.Task) -> None:
            if session_id in self._session_tasks:
                del self._session_tasks[session_id]
            if t.exception():
                logger.error(f"Session task {session_id} ended with exception: {t.exception()}")

        task.add_done_callback(on_task_done)

        return task

    async def _run_red_agent(self, session_id: str) -> None:
        """Run the Red Agent execution loop.

        Continuously executes Red Agent steps until completion,
        emitting events for each step and routing findings to
        the Blue Agent via the event queue.

        Args:
            session_id: Session identifier
        """
        logger.info(f"Red agent task started for session {session_id}")

        red_agent = self.red_agents[session_id]
        session = self.sessions[session_id]

        # Initial reconnaissance context
        context = f"Starting authorized security assessment of {session.target}. Scope: {session.scope or 'Full assessment'}"

        logger.info(f"Red agent entering main loop for session {session_id}")

        while red_agent.state not in (AgentStateEnum.COMPLETED, AgentStateEnum.ERROR):
            # Check for pause
            if session.status == SimulationStatus.PAUSED:
                await asyncio.sleep(1)
                continue

            # Check for stop
            if session.status in (SimulationStatus.COMPLETED, SimulationStatus.ERROR):
                break

            try:
                logger.info(f"Red agent running step for session {session_id}")
                # Execute one step
                result = await red_agent.run_step(context)
                logger.info(
                    f"Red agent step completed for session {session_id}: {result[:100] if result else 'No result'}"
                )

                # Emit event to Blue agent queue
                await self._emit_event(
                    session_id,
                    "red",
                    "step_complete",
                    {
                        "result": result[:500] if result else "",
                        "findings_count": len(red_agent.findings),
                        "steps_count": len(red_agent.steps),
                    },
                )

                # Update context for next iteration
                context = f"Previous step result:\n{result[:1000] if result else 'No result'}"

                # Small delay between steps
                await asyncio.sleep(2)

            except asyncio.CancelledError:
                logger.info(f"Red agent for session {session_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Red agent error in session {session_id}: {e}")
                await self._emit_event(
                    session_id,
                    "red",
                    "error",
                    {
                        "error": str(e),
                    },
                )
                break

        # Mark agent complete
        await self._emit_event(
            session_id,
            "red",
            "agent_complete",
            {
                "total_steps": len(red_agent.steps),
                "total_findings": len(red_agent.findings),
            },
        )
        # Signal Blue agent to stop waiting
        await self._emit_event(session_id, "red", "red_agent_done", {})

    async def _run_blue_agent(self, session_id: str) -> None:
        """Run the Blue Agent execution loop.

        Listens for events on the queue and responds to Red Agent
        activities in real-time.

        Args:
            session_id: Session identifier
        """
        blue_agent = self.blue_agents[session_id]
        session = self.sessions[session_id]
        event_queue = self._event_queues[session_id]

        while session.status in (SimulationStatus.RUNNING, SimulationStatus.PAUSED):
            # Check for pause
            if session.status == SimulationStatus.PAUSED:
                await asyncio.sleep(1)
                continue

            try:
                # Wait for events with timeout
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    # No event, continue monitoring
                    continue

                # Sentinel: Red agent finished — Blue agent can exit
                if event.get("agent") == "red" and event.get("event_type") == "red_agent_done":
                    logger.info(
                        f"Blue agent received red_agent_done sentinel for session {session_id}"
                    )
                    break

                # Process Red agent events
                if event.get("agent") == "red":
                    event_type = event.get("event_type", "")

                    # Respond to findings immediately
                    if event_type == "finding":
                        finding_data = event.get("data", {})
                        response = await blue_agent.respond_to_event(
                            {
                                "type": "red_agent_finding",
                                "source": "red_agent",
                                "severity": finding_data.get("severity", "medium"),
                                "data": finding_data,
                            }
                        )

                        await self._emit_event(
                            session_id,
                            "blue",
                            "response",
                            {
                                "response": response[:500] if response else "",
                            },
                        )

                    # Respond to step completions for situational awareness
                    elif event_type == "step_complete":
                        await self._emit_event(
                            session_id,
                            "blue",
                            "monitoring",
                            {
                                "red_steps": event.get("data", {}).get("steps_count", 0),
                            },
                        )

                    # Handle Red agent errors
                    elif event_type == "error":
                        await self._emit_event(
                            session_id,
                            "blue",
                            "alert",
                            {
                                "alert_type": "red_agent_error",
                                "message": event.get("data", {}).get("error", "Unknown error"),
                            },
                        )

            except asyncio.CancelledError:
                logger.info(f"Blue agent for session {session_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Blue agent error in session {session_id}: {e}")
                await self._emit_event(
                    session_id,
                    "blue",
                    "error",
                    {
                        "error": str(e),
                    },
                )

        # Mark agent complete
        await self._emit_event(
            session_id,
            "blue",
            "agent_complete",
            {
                "total_steps": len(blue_agent.steps),
                "total_findings": len(blue_agent.findings),
            },
        )

    async def _emit_event(
        self,
        session_id: str,
        agent: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Emit an event to the event queue and callback.

        Events are added to the session's event queue for inter-agent
        communication and stored in the session's event history.

        Args:
            session_id: Session identifier
            agent: Agent emitting the event
            event_type: Type of event
            data: Event payload
        """
        event = AgentEvent(
            session_id=session_id,
            agent=agent,
            event_type=event_type,
            data=data,
        )

        # Update session activity
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()

        # Add to queue for inter-agent communication
        if session_id in self._event_queues:
            try:
                self._event_queues[session_id].put_nowait(
                    {
                        "agent": agent,
                        "event_type": event_type,
                        "data": data,
                        "timestamp": event.timestamp.isoformat(),
                    }
                )
            except asyncio.QueueFull:
                logger.warning(
                    f"Event queue full for session {session_id}, dropping event: {event_type}"
                )

        # Call external callback for UI/WebSocket integration
        if self.on_event:
            try:
                self.on_event(event)
            except Exception as e:
                logger.warning(f"Event callback error: {e}")

        # Store in session history
        if session:
            session.events.append(
                {
                    "agent": agent,
                    "type": event_type,
                    "data": data,
                    "timestamp": event.timestamp.isoformat(),
                }
            )

        # Persist event to database (fire and forget)
        if self.use_database:
            asyncio.create_task(self._persist_event(session_id, agent, event_type, data))

    async def shutdown(self, timeout: float = 10.0) -> None:
        """Gracefully shutdown the orchestrator.

        Cancels all running sessions and cleanup tasks.

        Args:
            timeout: Seconds to wait for tasks to complete
        """
        logger.info("Shutting down orchestrator")
        self._shutdown_event.set()

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=timeout)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        # Cancel all session tasks
        for session_id, task in list(self._session_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=timeout)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

        # Stop all agents
        for session_id in list(self.sessions.keys()):
            try:
                if session_id in self.red_agents:
                    self.red_agents[session_id].stop()
                if session_id in self.blue_agents:
                    self.blue_agents[session_id].stop()
            except Exception as e:
                logger.warning(f"Error stopping agent for session {session_id}: {e}")

        logger.info("Orchestrator shutdown complete")

    def _safe_emit_event(
        self,
        session_id: str,
        agent: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Safely emit an event from a synchronous context.

        This method can be called from synchronous callbacks and will
        properly handle the async event emission.

        Args:
            session_id: Session identifier
            agent: Agent emitting the event
            event_type: Type of event
            data: Event payload
        """
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task
            asyncio.create_task(self._emit_event(session_id, agent, event_type, data))
        except RuntimeError:
            # No running loop - we're in a sync context
            # The event will be recorded in session history via _emit_event's sync parts
            # but won't be queued for async routing
            event = AgentEvent(
                session_id=session_id,
                agent=agent,
                event_type=event_type,
                data=data,
            )

            # Call external callback for UI/WebSocket integration
            if self.on_event:
                try:
                    self.on_event(event)
                except Exception as e:
                    logger.warning(f"Event callback error: {e}")

            # Store in session history
            session = self.sessions.get(session_id)
            if session:
                session.events.append(
                    {
                        "agent": agent,
                        "type": event_type,
                        "data": data,
                        "timestamp": event.timestamp.isoformat(),
                    }
                )

    def _handle_step(self, session_id: str, agent: str, step: Any) -> None:
        """Handle agent step callback.

        Emits a step event asynchronously.

        Args:
            session_id: Session identifier
            agent: Agent that completed the step
            step: Step object from the agent
        """
        self._safe_emit_event(
            session_id,
            agent,
            "step",
            {
                "step_num": step.step_num,
                "action": step.action.action_type,
                "success": step.success,
                "duration_ms": step.duration_ms,
            },
        )

    def _handle_finding(self, session_id: str, agent: str, finding: Finding) -> None:
        """Handle agent finding callback.

        Stores the finding in the session and emits a finding event.

        Args:
            session_id: Session identifier
            agent: Agent that found the issue
            finding: Finding object
        """
        session = self.sessions.get(session_id)
        if session:
            if agent == "red":
                session.red_findings.append(finding)
            else:
                session.blue_findings.append(finding)

        # Persist finding to database
        if self.use_database:
            asyncio.create_task(self._persist_finding(session_id, agent, finding))

        self._safe_emit_event(
            session_id,
            agent,
            "finding",
            {
                "title": finding.title,
                "severity": finding.severity,
                "description": finding.description[:200] if finding.description else "",
                "tool": finding.tool,
            },
        )

    def _handle_output(self, session_id: str, agent: str, message: str) -> None:
        """Handle agent output callback.

        Emits an output event for real-time logging.

        Args:
            session_id: Session identifier
            agent: Agent that produced the output
            message: Output message
        """
        self._safe_emit_event(
            session_id,
            agent,
            "output",
            {
                "message": message,
            },
        )

    def pause_session(self, session_id: str) -> bool:
        """Pause a running session.

        Sets the session status to PAUSED, which causes agents
        to pause their execution loops.

        Args:
            session_id: Session identifier

        Returns:
            True if paused, False if session not found or not running
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return False

        if session.status != SimulationStatus.RUNNING:
            logger.warning(f"Session {session_id} not running (status: {session.status.value})")
            return False

        session.status = SimulationStatus.PAUSED

        # Persist to database
        if self.use_database:
            asyncio.create_task(self._persist_session(session))

        # Pause agents
        if session_id in self.red_agents:
            self.red_agents[session_id].pause()
        if session_id in self.blue_agents:
            self.blue_agents[session_id].pause()

        logger.info(f"Session {session_id} paused")

        self._safe_emit_event(session_id, "orchestrator", "session_paused", {})
        return True

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session.

        Sets the session status back to RUNNING and resumes
        agent execution.

        Args:
            session_id: Session identifier

        Returns:
            True if resumed, False if session not found or not paused
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return False

        if session.status != SimulationStatus.PAUSED:
            logger.warning(f"Session {session_id} not paused (status: {session.status.value})")
            return False

        session.status = SimulationStatus.RUNNING

        # Persist to database
        if self.use_database:
            asyncio.create_task(self._persist_session(session))

        # Resume agents
        if session_id in self.red_agents:
            self.red_agents[session_id].resume()
        if session_id in self.blue_agents:
            self.blue_agents[session_id].resume()

        logger.info(f"Session {session_id} resumed")

        self._safe_emit_event(session_id, "orchestrator", "session_resumed", {})
        return True

    def stop_session(self, session_id: str) -> Optional[SimulationSession]:
        """Stop a session and return final state.

        Immediately stops the session, cancels any running tasks,
        and returns the final session state.

        Args:
            session_id: Session identifier

        Returns:
            Final Session state, or None if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        # Cancel background task if running
        if session_id in self._session_tasks:
            task = self._session_tasks[session_id]
            if not task.done():
                task.cancel()

        # Stop agents
        if session_id in self.red_agents:
            self.red_agents[session_id].stop()
        if session_id in self.blue_agents:
            self.blue_agents[session_id].stop()

        session.status = SimulationStatus.COMPLETED
        session.completed_at = datetime.utcnow()

        # Persist to database
        if self.use_database:
            asyncio.create_task(self._persist_session(session))

        logger.info(f"Session {session_id} stopped")

        self._safe_emit_event(
            session_id,
            "orchestrator",
            "session_stopped",
            {
                "red_findings": len(session.red_findings),
                "blue_findings": len(session.blue_findings),
            },
        )

        return session

    def get_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get metrics for a session.

        Returns comprehensive metrics including findings counts,
        step counts, duration, and agent summaries.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary of session metrics, empty if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return {}

        red_agent = self.red_agents.get(session_id)
        blue_agent = self.blue_agents.get(session_id)

        # Calculate duration
        if session.started_at:
            end_time = session.completed_at or datetime.utcnow()
            duration = end_time - session.started_at
            duration_str = str(duration).split(".")[0]  # Remove microseconds
        else:
            duration_str = "not started"

        # Count findings by severity
        def count_severity(findings: List[Finding]) -> Dict[str, int]:
            counts: Dict[str, int] = {}
            for f in findings:
                sev = f.severity.lower()
                counts[sev] = counts.get(sev, 0) + 1
            return counts

        return {
            "session_id": session_id,
            "target": session.target,
            "scope": session.scope,
            "status": session.status.value,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "duration": duration_str,
            "red_agent": {
                "steps": len(red_agent.steps) if red_agent else 0,
                "findings": len(session.red_findings),
                "findings_by_severity": count_severity(session.red_findings),
                "state": red_agent.state.value if red_agent else "unknown",
            },
            "blue_agent": {
                "steps": len(blue_agent.steps) if blue_agent else 0,
                "findings": len(session.blue_findings),
                "findings_by_severity": count_severity(session.blue_findings),
                "state": blue_agent.state.value if blue_agent else "unknown",
            },
            "total_findings": len(session.red_findings) + len(session.blue_findings),
            "total_events": len(session.events),
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get aggregate metrics for all sessions.

        Returns:
            Dictionary with aggregate statistics
        """
        sessions = list(self.sessions.values())

        status_counts: Dict[str, int] = {}
        total_red_findings = 0
        total_blue_findings = 0

        for session in sessions:
            status_counts[session.status.value] = status_counts.get(session.status.value, 0) + 1
            total_red_findings += len(session.red_findings)
            total_blue_findings += len(session.blue_findings)

        return {
            "total_sessions": len(sessions),
            "sessions_by_status": status_counts,
            "total_red_findings": total_red_findings,
            "total_blue_findings": total_blue_findings,
            "active_sessions": status_counts.get("running", 0) + status_counts.get("paused", 0),
        }

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and clean up resources.

        Stops the session if running and removes all associated data.
        Safe to call multiple times.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        # Mark as cleaning up to prevent race conditions
        old_status = session.status
        session.status = SimulationStatus.CLEANING_UP

        # Cancel background task first to prevent async events firing after cleanup
        if session_id in self._session_tasks:
            task = self._session_tasks[session_id]
            if not task.done():
                task.cancel()
            del self._session_tasks[session_id]

        # Stop agents (without emitting events since we're about to delete)
        if session_id in self.red_agents:
            try:
                self.red_agents[session_id].stop()
            except Exception as e:
                logger.debug(f"Error stopping red agent: {e}")
            del self.red_agents[session_id]

        if session_id in self.blue_agents:
            try:
                self.blue_agents[session_id].stop()
            except Exception as e:
                logger.debug(f"Error stopping blue agent: {e}")
            del self.blue_agents[session_id]

        # Update final status
        if old_status == SimulationStatus.RUNNING:
            session.status = SimulationStatus.COMPLETED
            session.completed_at = datetime.utcnow()
        else:
            session.status = old_status

        # Clean up all session data
        del self.sessions[session_id]
        del self._event_queues[session_id]
        self._initialized_sessions.discard(session_id)

        # Delete from database
        if self.use_database:
            asyncio.create_task(self._delete_session_from_db(session_id))

        logger.info(f"Session {session_id} deleted")
        return True

    async def _delete_session_from_db(self, session_id: str) -> None:
        """Delete session from database."""
        try:
            from purple_team_gpt.db.database import get_session as get_db_session
            from purple_team_gpt.db.repository import SessionRepository

            async with get_db_session() as db_session:
                repo = SessionRepository(db_session)
                await repo.delete_session(session_id)
        except Exception as e:
            logger.error(f"Failed to delete session from database: {e}")

    def get_active_session_count(self) -> int:
        """Get count of active (running/paused/pending) sessions."""
        return sum(
            1
            for s in self.sessions.values()
            if s.status
            in (SimulationStatus.RUNNING, SimulationStatus.PAUSED, SimulationStatus.PENDING)
        )


def create_orchestrator(
    engine: Optional[LLMEngine] = None, vector_store: Optional[VectorStore] = None, **kwargs
) -> PurpleOrchestrator:
    """Create a Purple Orchestrator instance.

    Convenience function that creates default engine and vector store
    if not provided.

    Args:
        engine: LLM engine (created if not provided)
        vector_store: Vector store (created if not provided)
        **kwargs: Additional arguments for PurpleOrchestrator

    Returns:
        Configured PurpleOrchestrator instance
    """
    if engine is None:
        from purple_team_gpt.core.llm import create_engine

        engine = create_engine()

    if vector_store is None:
        from purple_team_gpt.core.rag.vector_store import create_vector_store

        vector_store = create_vector_store()

    return PurpleOrchestrator(engine=engine, vector_store=vector_store, **kwargs)


# Backward compatibility aliases
SessionStatus = SimulationStatus
Session = SimulationSession
