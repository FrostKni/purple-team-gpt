"""Communication protocol for distributed Purple Team GPT.

This module defines the message types and protocol for communication
between the orchestrator and agent services.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class CommandType(str, Enum):
    """Types of commands sent from orchestrator to agents."""
    INITIALIZE = "initialize"
    EXECUTE_STEP = "execute_step"
    RESPOND_EVENT = "respond_event"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    GET_STATUS = "get_status"
    HEARTBEAT = "heartbeat"


class EventType(str, Enum):
    """Types of events sent from agents to orchestrator."""
    STEP_COMPLETE = "step_complete"
    FINDING = "finding"
    OUTPUT = "output"
    ERROR = "error"
    TOOL_START = "tool_start"
    TOOL_COMPLETE = "tool_complete"
    STATUS_CHANGE = "status_change"
    HEARTBEAT = "heartbeat"


class AgentStatus(str, Enum):
    """Agent operational status."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    OFFLINE = "offline"


class AgentRole(str, Enum):
    """Agent role types."""
    RED = "red"
    BLUE = "blue"


# ============== Base Messages ==============

class BaseMessage(BaseModel):
    """Base message structure for all communications."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    
    class Config:
        use_enum_values = True


# ============== Command Messages (Orchestrator -> Agent) ==============

class InitializePayload(BaseModel):
    """Payload for initialize command."""
    target: str
    scope: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecuteStepPayload(BaseModel):
    """Payload for execute_step command."""
    context: str
    max_steps: int = 1


class RespondEventPayload(BaseModel):
    """Payload for respond_event command (Blue agent)."""
    event_type: str
    source: str
    severity: str
    data: Dict[str, Any] = Field(default_factory=dict)


class CommandMessage(BaseMessage):
    """Command message sent from orchestrator to agent."""
    command_type: CommandType
    payload: Union[
        InitializePayload,
        ExecuteStepPayload,
        RespondEventPayload,
        Dict[str, Any]
    ] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


# ============== Event Messages (Agent -> Orchestrator) ==============

class StepCompleteData(BaseModel):
    """Data for step_complete event."""
    step_num: int
    action_type: str
    result: str
    success: bool
    duration_ms: float


class FindingData(BaseModel):
    """Data for finding event."""
    title: str
    severity: str
    description: str
    evidence: str = ""
    recommendation: str = ""
    tool: str = ""
    cve: Optional[str] = None
    cvss_score: Optional[float] = None


class ToolExecutionData(BaseModel):
    """Data for tool execution events."""
    tool_name: str
    command: str
    success: bool
    output: str = ""
    error: Optional[str] = None
    duration_ms: float = 0


class EventMessage(BaseMessage):
    """Event message sent from agent to orchestrator."""
    agent: AgentRole
    event_type: EventType
    data: Union[
        StepCompleteData,
        FindingData,
        ToolExecutionData,
        Dict[str, Any]
    ] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


# ============== Tool Execution Messages ==============

class ToolExecutionRequest(BaseMessage):
    """Request to execute a tool on an agent."""
    tool_name: str
    command: str
    timeout: int = 300
    safe_mode: bool = True


class ToolExecutionResponse(BaseMessage):
    """Response from tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    duration_ms: float = 0
    tool_name: str = ""
    command: str = ""


# ============== Agent Registration ==============

class AgentRegistration(BaseModel):
    """Agent registration request."""
    agent_id: str
    agent_type: AgentRole
    host: str
    port: int
    capabilities: List[str] = Field(default_factory=list)
    api_key: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class AgentInfo(BaseModel):
    """Information about a registered agent."""
    agent_id: str
    agent_type: AgentRole
    host: str
    port: int
    url: str
    capabilities: List[str] = Field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    last_heartbeat: Optional[datetime] = None
    current_session: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


# ============== Session Management ==============

class SessionStatus(str, Enum):
    """Session status types."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""
    target: str
    scope: str = ""
    red_agent_id: Optional[str] = None  # Auto-select if None
    blue_agent_id: Optional[str] = None  # Auto-select if None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionInfo(BaseModel):
    """Information about a session."""
    session_id: str
    target: str
    scope: str
    status: SessionStatus
    red_agent_id: Optional[str] = None
    blue_agent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    red_findings_count: int = 0
    blue_findings_count: int = 0
    events_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


# ============== WebSocket Messages ==============

class WSMessage(BaseModel):
    """WebSocket message structure."""
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSEventMessage(WSMessage):
    """WebSocket event message."""
    type: str = "event"
    agent: str
    event_type: str


class WSCommandMessage(WSMessage):
    """WebSocket command message."""
    type: str = "command"
    command: str
    params: Dict[str, Any] = Field(default_factory=dict)


class WSErrorMessage(WSMessage):
    """WebSocket error message."""
    type: str = "error"
    message: str
    code: Optional[int] = None