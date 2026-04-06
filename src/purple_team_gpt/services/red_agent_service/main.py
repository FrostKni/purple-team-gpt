"""Red Agent Service - Standalone service for offensive security operations.

This service runs on a dedicated attacker system with full access
to offensive security tools and target networks.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from purple_team_gpt.services.common.protocol import (
    CommandMessage,
    CommandType,
    EventMessage,
    EventType,
    AgentStatus,
    AgentRole,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from purple_team_gpt.services.common.executor import RemoteToolRunner, ToolResult
from purple_team_gpt.services.common.auth import AuthManager
from purple_team_gpt.core.llm.engine import LLMEngine, Conversation
from purple_team_gpt.config import get_settings

logger = logging.getLogger(__name__)


# Global state
class AgentState:
    """Runtime state for the agent service."""
    status: AgentStatus = AgentStatus.IDLE
    session_id: Optional[str] = None
    target: str = ""
    scope: str = ""
    conversation: Optional[Conversation] = None
    steps: list = []
    findings: list = []
    tool_runner: Optional[RemoteToolRunner] = None
    llm_engine: Optional[LLMEngine] = None
    orchestrator_url: str = ""
    event_queue: asyncio.Queue = asyncio.Queue()


agent_state = AgentState()
auth_manager: Optional[AuthManager] = None


def get_agent_state() -> AgentState:
    return agent_state


def get_auth_manager() -> AuthManager:
    global auth_manager
    if auth_manager is None:
        import os
        secret = os.getenv("SECRET_KEY", "red-agent-secret-key")
        auth_manager = AuthManager(secret)
    return auth_manager


async def verify_agent(
    x_api_key: str = Header(...),
    auth: AuthManager = Depends(get_auth_manager),
) -> str:
    """Verify API key and return agent ID."""
    agent_id = auth.verify_api_key(x_api_key)
    if not agent_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return agent_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    import os
    
    # Initialize
    logger.info("Starting Red Agent Service...")
    
    settings = get_settings()
    
    # Initialize tool runner
    agent_state.tool_runner = RemoteToolRunner(
        agent_type="red",
        safe_mode=os.getenv("SAFE_MODE", "true").lower() == "true",
        default_timeout=int(os.getenv("TOOL_TIMEOUT", "300")),
    )
    
    # Initialize LLM engine
    agent_state.llm_engine = LLMEngine(
        settings=settings.llm,
        openai_compatible_endpoints=settings.openai_compatible_endpoints,
    )
    
    # Get orchestrator URL
    agent_state.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
    
    # Register with orchestrator
    await register_with_orchestrator()
    
    # Start event sender task
    event_task = asyncio.create_task(event_sender_loop())
    
    logger.info("Red Agent Service ready")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Red Agent Service...")
    event_task.cancel()
    try:
        await event_task
    except asyncio.CancelledError:
        pass


async def register_with_orchestrator():
    """Register this agent with the orchestrator."""
    import os
    import aiohttp
    
    orchestrator_url = agent_state.orchestrator_url
    agent_id = os.getenv("AGENT_ID", "red-agent-1")
    agent_host = os.getenv("AGENT_HOST", "localhost")
    agent_port = int(os.getenv("AGENT_PORT", "8000"))
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{orchestrator_url}/api/v1/agents/register",
                json={
                    "agent_id": agent_id,
                    "agent_type": "red",
                    "host": agent_host,
                    "port": agent_port,
                    "capabilities": list(agent_state.tool_runner.allowed_tools),
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Store API key if provided
                    if "api_key" in data:
                        # Use for future requests
                        pass
                    logger.info(f"Registered with orchestrator at {orchestrator_url}")
                else:
                    logger.warning(f"Failed to register: {response.status}")
    except Exception as e:
        logger.warning(f"Could not register with orchestrator: {e}")


async def event_sender_loop():
    """Background task to send events to orchestrator."""
    import aiohttp
    
    while True:
        try:
            # Get event from queue
            event = await agent_state.event_queue.get()
            
            # Send to orchestrator
            if agent_state.orchestrator_url:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"{agent_state.orchestrator_url}/api/v1/events",
                        json=event.dict(),
                        timeout=aiohttp.ClientTimeout(total=10),
                    )
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Event send error: {e}")
            await asyncio.sleep(1)


# Create FastAPI app
app = FastAPI(
    title="Red Agent Service",
    description="Distributed offensive security agent",
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
        "service": "red-agent",
        "status": agent_state.status.value,
        "type": "red",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_status": agent_state.status.value,
        "current_session": agent_state.session_id,
    }


@app.get("/api/v1/status")
async def get_status():
    """Get detailed agent status."""
    return {
        "status": agent_state.status.value,
        "session_id": agent_state.session_id,
        "target": agent_state.target,
        "scope": agent_state.scope,
        "steps_count": len(agent_state.steps),
        "findings_count": len(agent_state.findings),
        "tool_stats": agent_state.tool_runner.get_stats() if agent_state.tool_runner else None,
    }


# ============== Command Endpoints ==============

@app.post("/api/v1/command")
async def receive_command(
    command: CommandMessage,
    state: AgentState = Depends(get_agent_state),
):
    """Receive and process a command from the orchestrator."""
    logger.info(f"Received command: {command.command_type}")
    
    try:
        if command.command_type == CommandType.INITIALIZE:
            return await handle_initialize(command, state)
        
        elif command.command_type == CommandType.EXECUTE_STEP:
            return await handle_execute_step(command, state)
        
        elif command.command_type == CommandType.PAUSE:
            return await handle_pause(state)
        
        elif command.command_type == CommandType.RESUME:
            return await handle_resume(state)
        
        elif command.command_type == CommandType.STOP:
            return await handle_stop(state)
        
        elif command.command_type == CommandType.GET_STATUS:
            return {"status": state.status.value}
        
        elif command.command_type == CommandType.HEARTBEAT:
            return {"status": "ok"}
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command type: {command.command_type}",
            )
    
    except Exception as e:
        logger.error(f"Command error: {e}")
        state.status = AgentStatus.ERROR
        raise HTTPException(status_code=500, detail=str(e))


async def handle_initialize(command: CommandMessage, state: AgentState):
    """Handle initialize command."""
    payload = command.payload
    
    state.target = payload.get("target", "")
    state.scope = payload.get("scope", "")
    state.session_id = command.session_id
    state.steps = []
    state.findings = []
    state.status = AgentStatus.INITIALIZING
    
    # Initialize conversation
    state.conversation = Conversation()
    state.conversation.system_prompt = get_red_agent_prompt()
    
    state.status = AgentStatus.RUNNING
    
    # Emit event
    await emit_event(EventType.STATUS_CHANGE, {
        "old_status": "idle",
        "new_status": "running",
    })
    
    return {
        "success": True,
        "message": f"Initialized for target: {state.target}",
    }


async def handle_execute_step(command: CommandMessage, state: AgentState):
    """Handle execute_step command."""
    if state.status != AgentStatus.RUNNING:
        return {
            "success": False,
            "error": f"Agent not running (status: {state.status.value})",
        }
    
    context = command.payload.get("context", "")
    
    # Get LLM response
    state.conversation.add_user(f"Context: {context}\n\nPlan your next action.")
    response = await state.llm_engine.chat(state.conversation)
    state.conversation.add_assistant(response)
    
    # Parse and execute actions
    actions = parse_actions(response)
    results = []
    
    for action in actions:
        result = await execute_action(action, state)
        results.append(result)
    
    # Emit step complete event
    await emit_event(EventType.STEP_COMPLETE, {
        "step_num": len(state.steps),
        "results": results,
    })
    
    return {
        "success": True,
        "step_num": len(state.steps),
        "results": results,
    }


async def handle_pause(state: AgentState):
    """Handle pause command."""
    state.status = AgentStatus.PAUSED
    await emit_event(EventType.STATUS_CHANGE, {"status": "paused"})
    return {"success": True, "status": "paused"}


async def handle_resume(state: AgentState):
    """Handle resume command."""
    state.status = AgentStatus.RUNNING
    await emit_event(EventType.STATUS_CHANGE, {"status": "running"})
    return {"success": True, "status": "running"}


async def handle_stop(state: AgentState):
    """Handle stop command."""
    state.status = AgentStatus.COMPLETED
    await emit_event(EventType.STATUS_CHANGE, {"status": "completed"})
    
    # Reset state
    state.session_id = None
    state.target = ""
    state.scope = ""
    state.status = AgentStatus.IDLE
    
    return {
        "success": True,
        "total_steps": len(state.steps),
        "total_findings": len(state.findings),
    }


# ============== Tool Execution Endpoints ==============

@app.post("/api/v1/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: ToolExecutionRequest,
    state: AgentState = Depends(get_agent_state),
):
    """Execute a tool directly (for testing)."""
    result = await state.tool_runner.execute(
        tool_name=request.tool_name,
        command=request.command,
        timeout=request.timeout,
    )
    
    return ToolExecutionResponse(
        message_id=request.message_id,
        session_id=request.session_id,
        success=result.success,
        output=result.output,
        error=result.error,
        return_code=result.return_code,
        duration_ms=result.duration_ms,
        tool_name=result.tool_name,
        command=result.command,
    )


# ============== Helper Functions ==============

async def emit_event(event_type: EventType, data: Dict[str, Any]):
    """Emit an event to the orchestrator."""
    event = EventMessage(
        session_id=agent_state.session_id,
        agent=AgentRole.RED,
        event_type=event_type,
        data=data,
    )
    await agent_state.event_queue.put(event)


async def execute_action(action: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
    """Execute a parsed action."""
    action_type = action.get("action_type", action.get("action", "unknown"))
    
    if action_type == "execute":
        result = await state.tool_runner.execute(
            tool_name=action.get("tool", ""),
            command=action.get("command", ""),
        )
        
        # Emit tool events
        await emit_event(EventType.TOOL_COMPLETE, {
            "tool": action.get("tool"),
            "success": result.success,
            "duration_ms": result.duration_ms,
        })
        
        state.steps.append({
            "action": action,
            "result": result.to_dict(),
        })
        
        return result.to_dict()
    
    elif action_type == "finding":
        finding = {
            "title": action.get("title", "Unknown Finding"),
            "severity": action.get("severity", "Medium"),
            "description": action.get("description", ""),
            "evidence": action.get("evidence", ""),
            "recommendation": action.get("recommendation", ""),
        }
        state.findings.append(finding)
        
        await emit_event(EventType.FINDING, finding)
        
        return {"success": True, "finding": finding}
    
    elif action_type == "complete":
        state.status = AgentStatus.COMPLETED
        return {"success": True, "message": "Assessment complete"}
    
    else:
        return {"success": False, "error": f"Unknown action: {action_type}"}


def parse_actions(response: str) -> list:
    """Parse action JSON from LLM response."""
    import json
    import re
    
    actions = []
    
    # Find JSON blocks
    pattern = r'```json\s*(.*?)\s*```'
    matches = re.findall(pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            data = json.loads(match.strip())
            actions.append(data)
        except json.JSONDecodeError:
            continue
    
    return actions


def get_red_agent_prompt() -> str:
    """Get the system prompt for the Red Agent."""
    return """You are the Red Agent, an autonomous offensive security testing AI.

IDENTITY:
You are part of Purple Team GPT, a cybersecurity simulation framework.
Your role is to perform authorized offensive security testing to identify
vulnerabilities before malicious actors can exploit them.

AVAILABLE TOOLS:
- nmap: Network/port scanning
- nikto: Web vulnerability scanning
- gobuster: Directory brute forcing
- sqlmap: SQL injection testing
- curl: HTTP requests
- dig: DNS enumeration
- whatweb: Web technology fingerprinting

SAFETY RULES:
1. ONLY test targets you have EXPLICIT authorization for
2. Never perform destructive operations
3. Respect rate limits
4. Document all actions

OUTPUT FORMAT:
To execute a tool:
```json
{
  "action": "execute",
  "tool": "nmap",
  "command": "nmap -sV -sC <target>",
  "explanation": "Service version detection"
}
```

To report a finding:
```json
{
  "action": "finding",
  "title": "Finding Title",
  "severity": "High",
  "description": "Description",
  "evidence": "Evidence",
  "recommendation": "Recommendation"
}
```

To complete assessment:
```json
{
  "action": "complete",
  "explanation": "Assessment complete"
}
```
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)