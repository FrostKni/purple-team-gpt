"""Distributed Orchestrator Service - Coordinates Red and Blue agents.

This service runs on a central management system and coordinates
distributed agent services over the network.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from purple_team_gpt.services.common.protocol import (
    CommandMessage,
    CommandType,
    EventMessage,
    EventType,
    AgentStatus,
    AgentRole,
    AgentInfo,
    AgentRegistration,
    SessionCreateRequest,
    SessionInfo,
    SessionStatus,
)
from purple_team_gpt.services.orchestrator_service.registry import AgentRegistry
from purple_team_gpt.services.common.auth import AuthManager
from purple_team_gpt.core.llm.engine import LLMEngine
from purple_team_gpt.core.rag.vector_store import VectorStore
from purple_team_gpt.config import get_settings

logger = logging.getLogger(__name__)


# Global state
class OrchestratorState:
    """Runtime state for the orchestrator."""
    agent_registry: Optional[AgentRegistry] = None
    sessions: Dict[str, SessionInfo] = {}
    session_events: Dict[str, List[EventMessage]] = {}
    event_queues: Dict[str, asyncio.Queue] = {}
    auth_manager: Optional[AuthManager] = None
    llm_engine: Optional[LLMEngine] = None
    vector_store: Optional[VectorStore] = None
    ws_manager: Optional["WebSocketManager"] = None


orchestrator_state = OrchestratorState()


class WebSocketManager:
    """Manages WebSocket connections for UI clients."""
    
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.connections:
            self.connections[session_id] = []
        self.connections[session_id].append(websocket)
        logger.debug(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.connections:
            if websocket in self.connections[session_id]:
                self.connections[session_id].remove(websocket)
            if not self.connections[session_id]:
                del self.connections[session_id]
    
    async def broadcast(self, session_id: str, message: dict):
        if session_id not in self.connections:
            return
        
        disconnected = []
        for ws in self.connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        
        for ws in disconnected:
            self.disconnect(ws, session_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    import os
    
    logger.info("Starting Orchestrator Service...")
    
    settings = get_settings()
    
    # Initialize components
    orchestrator_state.auth_manager = AuthManager(
        os.getenv("SECRET_KEY", "orchestrator-secret-key")
    )
    
    orchestrator_state.agent_registry = AgentRegistry(
        heartbeat_timeout=60,
        health_check_interval=30,
    )
    await orchestrator_state.agent_registry.start()
    
    # Set callbacks
    orchestrator_state.agent_registry.set_callbacks(
        on_online=lambda aid: logger.info(f"Agent online: {aid}"),
        on_offline=lambda aid: logger.warning(f"Agent offline: {aid}"),
    )
    
    orchestrator_state.ws_manager = WebSocketManager()
    
    # Initialize LLM and vector store (optional for distributed mode)
    try:
        orchestrator_state.llm_engine = LLMEngine(
            settings=settings.llm,
            openai_compatible_endpoints=settings.openai_compatible_endpoints,
        )
        logger.info("LLM engine initialized")
    except Exception as e:
        logger.warning(f"LLM engine not initialized: {e}")
    
    logger.info("Orchestrator Service ready")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Orchestrator Service...")
    await orchestrator_state.agent_registry.stop()


# Create FastAPI app
app = FastAPI(
    title="Orchestrator Service",
    description="Distributed Purple Team GPT Orchestrator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Status Endpoints ==============

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "orchestrator",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agents_registered": len(orchestrator_state.agent_registry.list_agents()),
        "active_sessions": len([
            s for s in orchestrator_state.sessions.values()
            if s.status == SessionStatus.RUNNING
        ]),
    }


@app.get("/api/v1/status")
async def get_status():
    """Get detailed orchestrator status."""
    return {
        "registry_stats": orchestrator_state.agent_registry.get_stats(),
        "sessions": {
            "total": len(orchestrator_state.sessions),
            "by_status": {
                status: len([s for s in orchestrator_state.sessions.values() if s.status == status])
                for status in SessionStatus
            },
        },
    }


# ============== Agent Management ==============

@app.get("/api/v1/agents")
async def list_agents(
    agent_type: Optional[AgentRole] = None,
    status: Optional[AgentStatus] = None,
):
    """List registered agents."""
    agents = orchestrator_state.agent_registry.list_agents(
        agent_type=agent_type,
        status=status,
    )
    return [a.dict() for a in agents]


@app.post("/api/v1/agents/register")
async def register_agent(registration: AgentRegistration):
    """Register a new agent."""
    agent_info = await orchestrator_state.agent_registry.register(registration)
    
    # Generate API key for agent
    api_key = orchestrator_state.auth_manager.register_agent(
        agent_id=registration.agent_id,
        agent_type=registration.agent_type,
    )
    
    return {
        "success": True,
        "agent_id": agent_info.agent_id,
        "api_key": api_key,
        "message": f"Agent {registration.agent_id} registered successfully",
    }


@app.delete("/api/v1/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """Unregister an agent."""
    success = orchestrator_state.agent_registry.unregister(agent_id)
    orchestrator_state.auth_manager.unregister_agent(agent_id)
    
    if success:
        return {"success": True, "message": f"Agent {agent_id} unregistered"}
    raise HTTPException(status_code=404, detail="Agent not found")


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent info."""
    agent = orchestrator_state.agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.dict()


# ============== Session Management ==============

@app.post("/api/v1/sessions")
async def create_session(request: SessionCreateRequest):
    """Create a new session."""
    import uuid
    
    session_id = str(uuid.uuid4())
    
    # Select agents
    red_agent_id = request.red_agent_id
    blue_agent_id = request.blue_agent_id
    
    if not red_agent_id:
        red_agent = orchestrator_state.agent_registry.select_agent(AgentRole.RED)
        red_agent_id = red_agent.agent_id if red_agent else None
    
    if not blue_agent_id:
        blue_agent = orchestrator_state.agent_registry.select_agent(AgentRole.BLUE)
        blue_agent_id = blue_agent.agent_id if blue_agent else None
    
    if not red_agent_id:
        raise HTTPException(
            status_code=400,
            detail="No Red agent available"
        )
    
    if not blue_agent_id:
        raise HTTPException(
            status_code=400,
            detail="No Blue agent available"
        )
    
    session = SessionInfo(
        session_id=session_id,
        target=request.target,
        scope=request.scope,
        status=SessionStatus.PENDING,
        red_agent_id=red_agent_id,
        blue_agent_id=blue_agent_id,
        metadata=request.metadata,
    )
    
    orchestrator_state.sessions[session_id] = session
    orchestrator_state.session_events[session_id] = []
    orchestrator_state.event_queues[session_id] = asyncio.Queue()
    
    logger.info(f"Created session {session_id}")
    
    return session.dict()


@app.get("/api/v1/sessions")
async def list_sessions(status: Optional[SessionStatus] = None):
    """List sessions."""
    sessions = list(orchestrator_state.sessions.values())
    if status:
        sessions = [s for s in sessions if s.status == status]
    return [s.dict() for s in sessions]


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session info."""
    session = orchestrator_state.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.dict()


@app.post("/api/v1/sessions/{session_id}/start")
async def start_session(session_id: str):
    """Start a session."""
    session = orchestrator_state.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != SessionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Session already {session.status.value}"
        )
    
    # Initialize agents
    import datetime
    
    # Send initialize command to Red agent
    red_result = await orchestrator_state.agent_registry.send_command(
        session.red_agent_id,
        {
            "command_type": CommandType.INITIALIZE,
            "session_id": session_id,
            "payload": {
                "target": session.target,
                "scope": session.scope,
            },
        },
    )
    
    if not red_result or not red_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Red agent: {red_result}"
        )
    
    # Send initialize command to Blue agent
    blue_result = await orchestrator_state.agent_registry.send_command(
        session.blue_agent_id,
        {
            "command_type": CommandType.INITIALIZE,
            "session_id": session_id,
            "payload": {
                "target": session.target,
                "scope": session.scope,
            },
        },
    )
    
    if not blue_result or not blue_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Blue agent: {blue_result}"
        )
    
    # Update session
    session.status = SessionStatus.RUNNING
    session.started_at = datetime.datetime.utcnow()
    
    # Start background task to run session
    asyncio.create_task(run_session(session_id))
    
    return {
        "success": True,
        "session": session.dict(),
    }


async def run_session(session_id: str):
    """Background task to run a session."""
    session = orchestrator_state.sessions.get(session_id)
    if not session:
        return
    
    logger.info(f"Starting session {session_id}")
    
    max_steps = 50
    step = 0
    
    while session.status == SessionStatus.RUNNING and step < max_steps:
        try:
            # Execute Red agent step
            red_result = await orchestrator_state.agent_registry.send_command(
                session.red_agent_id,
                {
                    "command_type": CommandType.EXECUTE_STEP,
                    "session_id": session_id,
                    "payload": {
                        "context": f"Step {step + 1} of assessment",
                    },
                },
                timeout=120,
            )
            
            if red_result:
                # Route findings to Blue agent
                await route_events_to_blue(session_id)
            
            step += 1
            
            # Small delay between steps
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Session {session_id} error: {e}")
            session.status = SessionStatus.ERROR
            break
    
    # Complete session
    if session.status == SessionStatus.RUNNING:
        session.status = SessionStatus.COMPLETED
        import datetime
        session.completed_at = datetime.datetime.utcnow()
    
    logger.info(f"Session {session_id} completed with status {session.status.value}")


async def route_events_to_blue(session_id: str):
    """Route events from Red agent to Blue agent."""
    session = orchestrator_state.sessions.get(session_id)
    if not session:
        return
    
    events = orchestrator_state.session_events.get(session_id, [])
    
    for event in events:
        if event.agent == AgentRole.RED and event.event_type == EventType.FINDING:
            await orchestrator_state.agent_registry.send_command(
                session.blue_agent_id,
                {
                    "command_type": CommandType.RESPOND_EVENT,
                    "session_id": session_id,
                    "payload": {
                        "event_type": event.event_type,
                        "source": "red_agent",
                        "severity": event.data.get("severity", "medium"),
                        "data": event.data,
                    },
                },
            )


@app.post("/api/v1/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    """Pause a session."""
    session = orchestrator_state.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Send pause to agents
    await orchestrator_state.agent_registry.send_command(
        session.red_agent_id,
        {"command_type": CommandType.PAUSE, "session_id": session_id},
    )
    await orchestrator_state.agent_registry.send_command(
        session.blue_agent_id,
        {"command_type": CommandType.PAUSE, "session_id": session_id},
    )
    
    session.status = SessionStatus.PAUSED
    return {"success": True, "status": "paused"}


@app.post("/api/v1/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """Resume a session."""
    session = orchestrator_state.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await orchestrator_state.agent_registry.send_command(
        session.red_agent_id,
        {"command_type": CommandType.RESUME, "session_id": session_id},
    )
    await orchestrator_state.agent_registry.send_command(
        session.blue_agent_id,
        {"command_type": CommandType.RESUME, "session_id": session_id},
    )
    
    session.status = SessionStatus.RUNNING
    return {"success": True, "status": "running"}


@app.post("/api/v1/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a session."""
    session = orchestrator_state.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Send stop to agents
    await orchestrator_state.agent_registry.send_command(
        session.red_agent_id,
        {"command_type": CommandType.STOP, "session_id": session_id},
    )
    await orchestrator_state.agent_registry.send_command(
        session.blue_agent_id,
        {"command_type": CommandType.STOP, "session_id": session_id},
    )
    
    import datetime
    session.status = SessionStatus.COMPLETED
    session.completed_at = datetime.datetime.utcnow()
    
    return {
        "success": True,
        "session": session.dict(),
    }


# ============== Event Handling ==============

@app.post("/api/v1/events")
async def receive_event(event: EventMessage):
    """Receive an event from an agent."""
    session_id = event.session_id
    
    if session_id and session_id in orchestrator_state.sessions:
        orchestrator_state.session_events[session_id].append(event)
        
        # Update session stats
        session = orchestrator_state.sessions[session_id]
        if event.event_type == EventType.FINDING:
            if event.agent == AgentRole.RED:
                session.red_findings_count += 1
            else:
                session.blue_findings_count += 1
        session.events_count += 1
        
        # Broadcast to WebSocket clients
        if orchestrator_state.ws_manager:
            await orchestrator_state.ws_manager.broadcast(session_id, {
                "type": "event",
                "agent": event.agent,
                "event_type": event.event_type,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
            })
    
    return {"success": True}


@app.get("/api/v1/sessions/{session_id}/events")
async def get_session_events(session_id: str):
    """Get events for a session."""
    if session_id not in orchestrator_state.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    events = orchestrator_state.session_events.get(session_id, [])
    return [e.dict() for e in events]


# ============== WebSocket Endpoint ==============

@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for UI clients."""
    session = orchestrator_state.sessions.get(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    await orchestrator_state.ws_manager.connect(websocket, session_id)
    
    try:
        # Send initial session state
        await websocket.send_json({
            "type": "session_state",
            "session": session.dict(),
        })
        
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (commands, feedback, etc.)
            import json
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        orchestrator_state.ws_manager.disconnect(websocket, session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)