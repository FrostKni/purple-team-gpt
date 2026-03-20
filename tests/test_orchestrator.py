"""Tests for the Purple Orchestrator."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# Session Tests
# ============================================================================

class TestSessionStatus:
    """Tests for the SessionStatus enum."""
    
    def test_status_values(self):
        """Test session status values."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        assert SessionStatus.PENDING.value == "pending"
        assert SessionStatus.RUNNING.value == "running"
        assert SessionStatus.PAUSED.value == "paused"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.ERROR.value == "error"


class TestSession:
    """Tests for the Session dataclass."""
    
    def test_session_creation(self):
        """Test creating a session."""
        from purple_team_gpt.core.orchestrator import Session
        session = Session(
            target="192.168.1.1",
            scope="Authorized test",
        )
        
        assert session.target == "192.168.1.1"
        assert session.scope == "Authorized test"
        assert session.id is not None
        assert session.created_at is not None
    
    def test_session_default_values(self):
        """Test session default values."""
        from purple_team_gpt.core.orchestrator import Session, SessionStatus
        session = Session()
        
        assert session.target == ""
        assert session.scope == ""
        assert session.status == SessionStatus.PENDING
        assert session.red_findings == []
        assert session.blue_findings == []
        assert session.events == []
        assert session.metadata == {}
    
    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        from purple_team_gpt.core.orchestrator import Session
        from purple_team_gpt.agents.base import Finding
        session = Session(
            target="192.168.1.1",
            scope="Test scope",
        )
        session.red_findings.append(Finding(title="Test", severity="High", description="Desc"))
        
        result = session.to_dict()
        
        assert result["target"] == "192.168.1.1"
        assert result["scope"] == "Test scope"
        assert result["red_findings_count"] == 1
        assert result["blue_findings_count"] == 0
    
    def test_session_with_findings(self):
        """Test session with findings."""
        from purple_team_gpt.core.orchestrator import Session
        from purple_team_gpt.agents.base import Finding
        session = Session()
        
        finding1 = Finding(title="Vuln 1", severity="High", description="Desc 1")
        finding2 = Finding(title="Vuln 2", severity="Medium", description="Desc 2")
        
        session.red_findings.append(finding1)
        session.blue_findings.append(finding2)
        
        assert len(session.red_findings) == 1
        assert len(session.blue_findings) == 1


class TestAgentEvent:
    """Tests for the AgentEvent dataclass."""
    
    def test_event_creation(self):
        """Test creating an agent event."""
        from purple_team_gpt.core.orchestrator import AgentEvent
        event = AgentEvent(
            session_id="test-session",
            agent="red",
            event_type="finding",
            data={"title": "Test Finding"},
        )
        
        assert event.session_id == "test-session"
        assert event.agent == "red"
        assert event.event_type == "finding"
        assert event.data["title"] == "Test Finding"
        assert event.timestamp is not None
    
    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        from purple_team_gpt.core.orchestrator import AgentEvent
        event = AgentEvent(
            session_id="session-123",
            agent="blue",
            event_type="detection",
            data={"threat": "malware"},
        )
        
        result = event.to_dict()
        
        assert result["session_id"] == "session-123"
        assert result["agent"] == "blue"
        assert result["event_type"] == "detection"
        assert "timestamp" in result


# ============================================================================
# Orchestrator Tests
# ============================================================================

class TestPurpleOrchestrator:
    """Tests for the PurpleOrchestrator class."""
    
    def test_initialization(self, llm_engine, vector_store):
        """Test orchestrator initialization."""
        from purple_team_gpt.core.orchestrator import PurpleOrchestrator
        orchestrator = PurpleOrchestrator(
            engine=llm_engine,
            vector_store=vector_store,
            max_steps=50,
            safe_mode=True,
        )
        
        assert orchestrator.engine == llm_engine
        assert orchestrator.vector_store == vector_store
        assert orchestrator.max_steps == 50
        assert orchestrator.safe_mode is True
        assert orchestrator.sessions == {}
    
    def test_initialization_with_callback(self, llm_engine, vector_store, mock_event_callback):
        """Test orchestrator initialization with event callback."""
        from purple_team_gpt.core.orchestrator import PurpleOrchestrator
        orchestrator = PurpleOrchestrator(
            engine=llm_engine,
            vector_store=vector_store,
            on_event=mock_event_callback,
        )
        
        assert orchestrator.on_event == mock_event_callback
    
    def test_create_session(self, orchestrator):
        """Test creating a session."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        session = orchestrator.create_session(
            target="192.168.1.1",
            scope="Authorized penetration test",
        )
        
        assert session.target == "192.168.1.1"
        assert session.scope == "Authorized penetration test"
        assert session.status == SessionStatus.PENDING
        assert session.id in orchestrator.sessions
    
    def test_create_session_creates_agents(self, orchestrator):
        """Test that creating a session creates red and blue agents."""
        session = orchestrator.create_session("192.168.1.1")
        
        assert session.id in orchestrator.red_agents
        assert session.id in orchestrator.blue_agents
    
    def test_create_session_with_metadata(self, orchestrator):
        """Test creating a session with metadata."""
        session = orchestrator.create_session(
            target="target",
            metadata={"owner": "security-team", "priority": "high"},
        )
        
        assert session.metadata["owner"] == "security-team"
        assert session.metadata["priority"] == "high"
    
    def test_create_session_event_queue(self, orchestrator):
        """Test that creating a session creates an event queue."""
        session = orchestrator.create_session("target")
        
        assert session.id in orchestrator._event_queues
    
    def test_get_session(self, orchestrator):
        """Test getting a session by ID."""
        created = orchestrator.create_session("192.168.1.1")
        
        retrieved = orchestrator.get_session(created.id)
        
        assert retrieved == created
    
    def test_get_session_not_found(self, orchestrator):
        """Test getting a non-existent session."""
        result = orchestrator.get_session("nonexistent-id")
        assert result is None
    
    def test_list_sessions(self, orchestrator):
        """Test listing all sessions."""
        orchestrator.create_session("target1")
        orchestrator.create_session("target2")
        
        sessions = orchestrator.list_sessions()
        
        assert len(sessions) == 2
    
    def test_list_sessions_filtered(self, orchestrator):
        """Test listing sessions filtered by status."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        session1 = orchestrator.create_session("target1")
        session2 = orchestrator.create_session("target2")
        
        # Modify status
        orchestrator.sessions[session1.id].status = SessionStatus.RUNNING
        
        running = orchestrator.list_sessions(status=SessionStatus.RUNNING)
        pending = orchestrator.list_sessions(status=SessionStatus.PENDING)
        
        assert len(running) == 1
        assert len(pending) == 1
    
    def test_pause_session(self, orchestrator):
        """Test pausing a session."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        session = orchestrator.create_session("target")
        session.status = SessionStatus.RUNNING
        
        result = orchestrator.pause_session(session.id)
        
        assert result is True
        assert session.status == SessionStatus.PAUSED
    
    def test_pause_session_not_running(self, orchestrator):
        """Test pausing a session that's not running."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        session = orchestrator.create_session("target")
        
        result = orchestrator.pause_session(session.id)
        
        assert result is False
        assert session.status == SessionStatus.PENDING
    
    def test_pause_session_not_found(self, orchestrator):
        """Test pausing a non-existent session."""
        result = orchestrator.pause_session("nonexistent")
        assert result is False
    
    def test_resume_session(self, orchestrator):
        """Test resuming a paused session."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        session = orchestrator.create_session("target")
        session.status = SessionStatus.PAUSED
        
        result = orchestrator.resume_session(session.id)
        
        assert result is True
        assert session.status == SessionStatus.RUNNING
    
    def test_resume_session_not_paused(self, orchestrator):
        """Test resuming a session that's not paused."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        session = orchestrator.create_session("target")
        
        result = orchestrator.resume_session(session.id)
        
        assert result is False
    
    def test_stop_session(self, orchestrator):
        """Test stopping a session."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        session = orchestrator.create_session("target")
        session.status = SessionStatus.RUNNING
        
        result = orchestrator.stop_session(session.id)
        
        assert result == session
        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None
    
    def test_stop_session_not_found(self, orchestrator):
        """Test stopping a non-existent session."""
        result = orchestrator.stop_session("nonexistent")
        assert result is None
    
    def test_delete_session(self, orchestrator):
        """Test deleting a session."""
        session = orchestrator.create_session("target")
        
        result = orchestrator.delete_session(session.id)
        
        assert result is True
        assert session.id not in orchestrator.sessions
        assert session.id not in orchestrator.red_agents
        assert session.id not in orchestrator.blue_agents
    
    def test_delete_session_not_found(self, orchestrator):
        """Test deleting a non-existent session."""
        result = orchestrator.delete_session("nonexistent")
        assert result is False
    
    def test_get_metrics(self, orchestrator):
        """Test getting session metrics."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        from purple_team_gpt.agents.base import Finding
        session = orchestrator.create_session("target")
        session.status = SessionStatus.RUNNING
        session.started_at = datetime.utcnow()
        session.red_findings.append(Finding(title="Vuln", severity="High", description="Desc"))
        session.blue_findings.append(Finding(title="Detect", severity="Medium", description="Desc"))
        
        metrics = orchestrator.get_metrics(session.id)
        
        assert metrics["session_id"] == session.id
        assert metrics["target"] == "target"
        assert metrics["status"] == "running"
        assert metrics["red_agent"]["findings"] == 1
        assert metrics["blue_agent"]["findings"] == 1
        assert metrics["total_findings"] == 2
    
    def test_get_metrics_not_found(self, orchestrator):
        """Test getting metrics for non-existent session."""
        metrics = orchestrator.get_metrics("nonexistent")
        assert metrics == {}
    
    def test_get_all_metrics(self, orchestrator):
        """Test getting aggregate metrics."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        orchestrator.create_session("target1")
        orchestrator.create_session("target2")
        
        session3 = orchestrator.create_session("target3")
        session3.status = SessionStatus.RUNNING
        
        metrics = orchestrator.get_all_metrics()
        
        assert metrics["total_sessions"] == 3
        assert metrics["sessions_by_status"]["pending"] == 2
        assert metrics["sessions_by_status"]["running"] == 1
        assert metrics["active_sessions"] == 1
    
    def test_handle_finding_red(self, orchestrator):
        """Test handling a red agent finding."""
        from purple_team_gpt.agents.base import Finding
        session = orchestrator.create_session("target")
        finding = Finding(title="Red Finding", severity="High", description="Test")
        
        orchestrator._handle_finding(session.id, "red", finding)
        
        assert finding in session.red_findings
        assert finding not in session.blue_findings
    
    def test_handle_finding_blue(self, orchestrator):
        """Test handling a blue agent finding."""
        from purple_team_gpt.agents.base import Finding
        session = orchestrator.create_session("target")
        finding = Finding(title="Blue Finding", severity="Medium", description="Test")
        
        orchestrator._handle_finding(session.id, "blue", finding)
        
        assert finding in session.blue_findings
        assert finding not in session.red_findings
    
    def test_handle_step(self, orchestrator):
        """Test handling an agent step."""
        from purple_team_gpt.agents.base import AgentAction, AgentStep
        session = orchestrator.create_session("target")
        
        action = AgentAction(action_type="execute", tool="nmap")
        step = AgentStep(step_num=1, action=action, success=True)
        
        # Should not raise
        orchestrator._handle_step(session.id, "red", step)
    
    def test_handle_output(self, orchestrator):
        """Test handling agent output."""
        session = orchestrator.create_session("target")
        
        # Should not raise
        orchestrator._handle_output(session.id, "red", "Test output message")
    
    @pytest.mark.asyncio
    async def test_emit_event(self, llm_engine, vector_store, mock_event_callback):
        """Test emitting an event."""
        from purple_team_gpt.core.orchestrator import PurpleOrchestrator
        
        # Create orchestrator WITH the callback
        orchestrator = PurpleOrchestrator(
            engine=llm_engine,
            vector_store=vector_store,
            on_event=mock_event_callback,
        )
        
        session = orchestrator.create_session("target")
        
        await orchestrator._emit_event(
            session.id,
            "red",
            "finding",
            {"title": "Test Finding"},
        )
        
        # Event should be in queue
        queue = orchestrator._event_queues[session.id]
        assert not queue.empty()
        
        # Callback should be called
        mock_event_callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_emit_event_stores_in_history(self, orchestrator):
        """Test that emitted events are stored in session history."""
        session = orchestrator.create_session("target")
        
        await orchestrator._emit_event(
            session.id,
            "red",
            "step",
            {"action": "scan"},
        )
        
        assert len(session.events) == 1
        assert session.events[0]["agent"] == "red"
        assert session.events[0]["type"] == "step"


class TestPurpleOrchestratorAsync:
    """Async tests for PurpleOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_start_session_sets_status(self, orchestrator):
        """Test that start_session sets the correct status."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        from purple_team_gpt.agents.base import AgentState
        session = orchestrator.create_session("target")
        
        # Mock agent run_step to complete immediately
        async def mock_run_step(context):
            orchestrator.red_agents[session.id].state = AgentState.COMPLETED
            return "Done"
        
        orchestrator.red_agents[session.id].run_step = mock_run_step
        orchestrator.blue_agents[session.id].respond_to_event = AsyncMock(return_value="Response")
        
        # Start and wait briefly
        task = asyncio.create_task(orchestrator.start_session(session.id))
        
        # Let it run briefly then check status
        await asyncio.sleep(0.1)
        
        # Should be running
        assert session.status in (SessionStatus.RUNNING, SessionStatus.COMPLETED)
        
        # Cancel the task if still running
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_start_session_not_found(self, orchestrator):
        """Test starting a non-existent session."""
        with pytest.raises(ValueError, match="not found"):
            await orchestrator.start_session("nonexistent-id")
    
    @pytest.mark.asyncio
    async def test_start_session_already_running(self, orchestrator):
        """Test starting an already running session."""
        from purple_team_gpt.core.orchestrator import SessionStatus
        session = orchestrator.create_session("target")
        session.status = SessionStatus.RUNNING
        
        # Should return without error
        await orchestrator.start_session(session.id)
    
    def test_start_session_background(self, orchestrator):
        """Test starting a session in the background."""
        import asyncio
        session = orchestrator.create_session("target")
        
        # Mock the agents to prevent actual execution
        orchestrator.red_agents[session.id].run_step = AsyncMock(return_value="Done")
        orchestrator.blue_agents[session.id].respond_to_event = AsyncMock(return_value="Response")
        
        # Need to be in async context for create_task
        async def run_test():
            task = orchestrator.start_session_background(session.id)
            
            assert task is not None
            assert session.id in orchestrator._session_tasks
            
            # Clean up
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        asyncio.run(run_test())
    
    def test_start_session_background_already_running(self, orchestrator):
        """Test starting background session when already running."""
        session = orchestrator.create_session("target")
        
        # Create a fake running task
        fake_task = MagicMock()
        fake_task.done.return_value = False
        orchestrator._session_tasks[session.id] = fake_task
        
        task = orchestrator.start_session_background(session.id)
        
        # Should return the existing task
        assert task == fake_task


class TestCreateOrchestrator:
    """Tests for the create_orchestrator factory function."""
    
    def test_create_with_dependencies(self, llm_engine, vector_store):
        """Test creating orchestrator with provided dependencies."""
        from purple_team_gpt.core.orchestrator import create_orchestrator
        orchestrator = create_orchestrator(
            engine=llm_engine,
            vector_store=vector_store,
        )
        
        assert orchestrator.engine == llm_engine
        assert orchestrator.vector_store == vector_store
    
    def test_create_with_defaults(self):
        """Test creating orchestrator with default dependencies."""
        from purple_team_gpt.core.orchestrator import create_orchestrator
        
        # Create mock engine and vector store
        mock_engine = MagicMock()
        mock_vs = MagicMock()
        
        # Patch where the functions are imported from in orchestrator.py
        with patch("purple_team_gpt.core.llm.create_engine", return_value=mock_engine):
            with patch("purple_team_gpt.core.rag.vector_store.create_vector_store", return_value=mock_vs):
                orchestrator = create_orchestrator()
                
                assert orchestrator is not None
    
    def test_create_with_kwargs(self, llm_engine, vector_store):
        """Test creating orchestrator with additional kwargs."""
        from purple_team_gpt.core.orchestrator import create_orchestrator
        orchestrator = create_orchestrator(
            engine=llm_engine,
            vector_store=vector_store,
            max_steps=100,
            safe_mode=False,
        )
        
        assert orchestrator.max_steps == 100
        assert orchestrator.safe_mode is False