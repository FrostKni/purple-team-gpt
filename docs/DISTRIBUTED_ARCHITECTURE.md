# Distributed Purple Team GPT Architecture

## Executive Summary

This document outlines the transformation of Purple Team GPT from a monolithic application into a distributed architecture where Red Agent, Blue Agent, and Orchestrator run as independent services on separate systems.

## Current Architecture (Monolithic)

```
┌─────────────────────────────────────────────────────────────┐
│                    Single Host System                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              FastAPI Backend                          │    │
│  │  ┌──────────────┐  ┌──────────────┐                  │    │
│  │  │ Orchestrator │  │  WebSocket   │                  │    │
│  │  └──────┬───────┘  └──────────────┘                  │    │
│  │         │                                             │    │
│  │  ┌──────┴───────┐  ┌──────────────┐                  │    │
│  │  │  Red Agent   │  │ Blue Agent   │                  │    │
│  │  │  (in-memory) │  │ (in-memory)  │                  │    │
│  │  └──────────────┘  └──────────────┘                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Tools execute locally on same system                        │
└─────────────────────────────────────────────────────────────┘
```

## Proposed Distributed Architecture

```
                              ┌─────────────────────────┐
                              │    Orchestrator Host    │
                              │  ┌───────────────────┐  │
                              │  │   Orchestrator    │  │
                              │  │     Service       │  │
                              │  │  (FastAPI + WS)   │  │
                              │  └────────┬──────────┘  │
                              │           │             │
                              │    Message Router       │
                              └───────────┬─────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     │                     ▼
    ┌───────────────────────────┐         │         ┌───────────────────────────┐
    │     Red Agent Host        │         │         │    Blue Agent Host        │
    │  (Attacker System)        │         │         │  (Defender System)        │
    │  ┌─────────────────────┐  │         │         │  ┌─────────────────────┐  │
    │  │   Red Agent         │  │         │         │  │   Blue Agent        │  │
    │  │   Service           │  │         │         │  │   Service           │  │
    │  │   (FastAPI)         │◄─┼─────────┼─────────┼─►│   (FastAPI)         │  │
    │  └─────────┬───────────┘  │         │         │  └─────────┬───────────┘  │
    │            │              │         │         │            │              │
    │  ┌─────────┴───────────┐  │         │         │  ┌─────────┴───────────┐  │
    │  │  Tool Executor      │  │         │         │  │  Tool Executor      │  │
    │  │  - nmap             │  │         │         │  │  - log_analyzer     │  │
    │  │  - nikto            │  │         │         │  │  - firewall_mgr     │  │
    │  │  - gobuster         │  │         │         │  │  - process_monitor  │  │
    │  │  - sqlmap           │  │         │         │  │  - netstat          │  │
    │  └─────────────────────┘  │         │         │  └─────────────────────┘  │
    └───────────────────────────┘         │         └───────────────────────────┘
                                          │
                                          ▼
                              ┌─────────────────────────┐
                              │      Target Network     │
                              │   (Assessment Scope)    │
                              └─────────────────────────┘
```

## 1. Agent Service Architecture

### 1.1 Red Agent Service

**Location**: `src/purple_team_gpt/services/red_agent_service/`

```
red_agent_service/
├── __init__.py
├── main.py                 # FastAPI entry point
├── agent.py                # RedAgent wrapper for service
├── routers/
│   ├── __init__.py
│   ├── commands.py         # Receive commands from orchestrator
│   ├── status.py           # Health and status endpoints
│   └── tools.py            # Tool execution endpoints
├── executor/
│   ├── __init__.py
│   ├── tool_runner.py      # Remote tool execution
│   └── sandbox.py          # Optional sandboxing
├── config.py               # Service-specific config
└── Dockerfile
```

### 1.2 Blue Agent Service

**Location**: `src/purple_team_gpt/services/blue_agent_service/`

```
blue_agent_service/
├── __init__.py
├── main.py                 # FastAPI entry point
├── agent.py                # BlueAgent wrapper for service
├── routers/
│   ├── __init__.py
│   ├── commands.py         # Receive commands from orchestrator
│   ├── events.py           # Receive Red agent events
│   ├── status.py           # Health and status endpoints
│   └── tools.py            # Tool execution endpoints
├── executor/
│   ├── __init__.py
│   ├── tool_runner.py      # Remote tool execution
│   └── monitor.py          # System monitoring
├── config.py               # Service-specific config
└── Dockerfile
```

### 1.3 Orchestrator Service

**Location**: `src/purple_team_gpt/services/orchestrator_service/`

```
orchestrator_service/
├── __init__.py
├── main.py                 # FastAPI entry point
├── orchestrator.py         # Remote orchestrator
├── routers/
│   ├── __init__.py
│   ├── sessions.py         # Session management
│   ├── agents.py           # Agent registration/discovery
│   └── websocket.py        # Real-time updates to UI
├── registry/
│   ├── __init__.py
│   ├── agent_registry.py   # Agent discovery and health
│   └── connection_pool.py  # Connection management
├── config.py               # Service-specific config
└── Dockerfile
```

## 2. Communication Protocol

### 2.1 Protocol Overview

We use a hybrid protocol:
- **HTTP/REST** for synchronous operations (commands, status)
- **WebSocket** for real-time events and streaming
- **gRPC** (optional) for high-performance tool execution

### 2.2 Message Types

```python
# Base message structure
class BaseMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    
# Command messages (Orchestrator -> Agent)
class CommandMessage(BaseMessage):
    command_type: Literal[
        "initialize",      # Initialize agent with target/scope
        "execute_step",    # Execute one planning/execution step
        "respond_event",   # Respond to an event (Blue agent)
        "pause",           # Pause execution
        "resume",          # Resume execution
        "stop",            # Stop and cleanup
        "get_status",      # Get current status
    ]
    payload: Dict[str, Any] = Field(default_factory=dict)
    
# Event messages (Agent -> Orchestrator)
class EventMessage(BaseMessage):
    agent: Literal["red", "blue"]
    event_type: Literal[
        "step_complete",   # Step execution complete
        "finding",         # Security finding
        "output",          # Output message
        "error",           # Error occurred
        "tool_start",      # Tool execution started
        "tool_complete",   # Tool execution complete
        "status_change",   # Agent status changed
    ]
    data: Dict[str, Any] = Field(default_factory=dict)
    
# Tool execution messages
class ToolExecutionRequest(BaseMessage):
    tool_name: str
    command: str
    timeout: int = 300
    safe_mode: bool = True
    
class ToolExecutionResponse(BaseMessage):
    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    duration_ms: float = 0
```

### 2.3 API Endpoints

#### Red Agent Service Endpoints

```python
# POST /api/v1/command
# Receive command from orchestrator
@router.post("/command")
async def receive_command(command: CommandMessage) -> Dict[str, Any]:

# GET /api/v1/status
# Get agent status
@router.get("/status")
async def get_status() -> AgentStatus:

# POST /api/v1/execute
# Direct tool execution (for testing)
@router.post("/execute")
async def execute_tool(request: ToolExecutionRequest) -> ToolExecutionResponse:

# WS /ws/events
# WebSocket for streaming events to orchestrator
@router.websocket("/ws/events")
async def event_stream(websocket: WebSocket):
```

#### Blue Agent Service Endpoints

```python
# POST /api/v1/command
# Receive command from orchestrator
@router.post("/command")
async def receive_command(command: CommandMessage) -> Dict[str, Any]:

# POST /api/v1/event
# Receive Red agent event for response
@router.post("/event")
async def receive_event(event: EventMessage) -> Dict[str, Any]:

# GET /api/v1/status
# Get agent status
@router.get("/status")
async def get_status() -> AgentStatus:

# WS /ws/events
# WebSocket for streaming events to orchestrator
@router.websocket("/ws/events")
async def event_stream(websocket: WebSocket):
```

#### Orchestrator Service Endpoints

```python
# POST /api/v1/sessions
# Create new session
@router.post("/sessions")
async def create_session(request: SessionCreateRequest) -> Session:

# POST /api/v1/sessions/{session_id}/start
# Start session with registered agents
@router.post("/sessions/{session_id}/start")
async def start_session(session_id: str) -> Dict[str, Any]:

# GET /api/v1/agents
# List registered agents
@router.get("/agents")
async def list_agents() -> List[AgentInfo]:

# POST /api/v1/agents/register
# Register agent with orchestrator
@router.post("/agents/register")
async def register_agent(info: AgentRegistration) -> Dict[str, Any]:

# WS /ws/session/{session_id}
# WebSocket for UI clients
@router.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
```

### 2.4 Communication Flow

```
1. Agent Registration:
   Agent Service --[POST /agents/register]--> Orchestrator
   Orchestrator validates and stores agent info
   Orchestrator --[WebSocket /ws/events]--> Agent (establish event stream)

2. Session Creation:
   UI Client --[POST /sessions]--> Orchestrator
   Orchestrator creates session, selects agents

3. Session Start:
   UI Client --[POST /sessions/{id}/start]--> Orchestrator
   Orchestrator --[POST /command initialize]--> Red Agent
   Orchestrator --[POST /command initialize]--> Blue Agent

4. Execution Loop:
   Orchestrator --[POST /command execute_step]--> Red Agent
   Red Agent executes, emits events via WebSocket
   Red Agent --[WebSocket event]--> Orchestrator
   Orchestrator --[POST /event]--> Blue Agent (if relevant)
   Blue Agent responds, emits events
   Orchestrator broadcasts to UI clients

5. Session End:
   Orchestrator --[POST /command stop]--> Red Agent
   Orchestrator --[POST /command stop]--> Blue Agent
   Orchestrator finalizes session
```

## 3. Network Topology Options

### 3.1 Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  orchestrator:
    build:
      context: .
      dockerfile: src/purple_team_gpt/services/orchestrator_service/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ORCHESTRATOR_HOST=0.0.0.0
      - ORCHESTRATOR_PORT=8000
    networks:
      - purple-team-net
    depends_on:
      - chromadb

  red-agent:
    build:
      context: .
      dockerfile: src/purple_team_gpt/services/red_agent_service/Dockerfile
    ports:
      - "8001:8000"
    environment:
      - AGENT_TYPE=red
      - ORCHESTRATOR_URL=http://orchestrator:8000
      - AGENT_HOST=red-agent
      - AGENT_PORT=8000
    networks:
      - purple-team-net
    # Privileged for network tools (nmap, etc.)
    privileged: true
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: "bridge"

  blue-agent:
    build:
      context: .
      dockerfile: src/purple_team_gpt/services/blue_agent_service/Dockerfile
    ports:
      - "8002:8000"
    environment:
      - AGENT_TYPE=blue
      - ORCHESTRATOR_URL=http://orchestrator:8000
      - AGENT_HOST=blue-agent
      - AGENT_PORT=8000
    networks:
      - purple-team-net
    volumes:
      - /var/log:/var/log:ro
      - /etc:/etc:ro

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8003:8000"
    volumes:
      - chromadb-data:/chroma/data
    networks:
      - purple-team-net

networks:
  purple-team-net:
    driver: bridge

volumes:
  chromadb-data:
```

### 3.2 Kubernetes (Production)

```yaml
# kubernetes/orchestrator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
    spec:
      containers:
      - name: orchestrator
        image: purple-team-gpt/orchestrator:latest
        ports:
        - containerPort: 8000
        env:
        - name: ORCHESTRATOR_HOST
          value: "0.0.0.0"
        - name: CHROMA_HOST
          value: "chromadb-service"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"

---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator-service
spec:
  selector:
    app: orchestrator
  ports:
  - port: 8000
    targetPort: 8000

---
# kubernetes/red-agent-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: red-agent
spec:
  selector:
    matchLabels:
      app: red-agent
  template:
    metadata:
      labels:
        app: red-agent
    spec:
      hostNetwork: true  # Access to host network
      containers:
      - name: red-agent
        image: purple-team-gpt/red-agent:latest
        securityContext:
          privileged: true
          capabilities:
            add:
            - NET_ADMIN
            - NET_RAW
        env:
        - name: ORCHESTRATOR_URL
          value: "http://orchestrator-service:8000"
        - name: AGENT_HOST
          valueFrom:
            fieldRef:
              fieldPath: status.podIP

---
# kubernetes/blue-agent-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: blue-agent
spec:
  selector:
    matchLabels:
      app: blue-agent
  template:
    metadata:
      labels:
        app: blue-agent
    spec:
      hostNetwork: true  # Monitor host network
      containers:
      - name: blue-agent
        image: purple-team-gpt/blue-agent:latest
        securityContext:
          privileged: true
        volumeMounts:
        - name: var-log
          mountPath: /var/log
          readOnly: true
        - name: etc
          mountPath: /etc
          readOnly: true
        env:
        - name: ORCHESTRATOR_URL
          value: "http://orchestrator-service:8000"
      volumes:
      - name: var-log
        hostPath:
          path: /var/log
      - name: etc
        hostPath:
          path: /etc
```

### 3.3 Physical/Virtual Machines

For air-gapped environments or maximum isolation:

```
┌──────────────────────────────────────────────────────────────────┐
│                      Management Network                           │
│                   (10.0.0.0/24 - Isolated)                        │
│                                                                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐         │
│  │ Orchestrator│     │  Red Agent  │     │ Blue Agent  │         │
│  │   10.0.0.10 │◄───►│  10.0.0.11  │◄───►│  10.0.0.12  │         │
│  └─────────────┘     └──────┬──────┘     └─────────────┘         │
│                             │                                     │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
                              │ Attack Network
                              │ (192.168.100.0/24)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Target 1 │   │ Target 2 │   │ Target 3 │
        └──────────┘   └──────────┘   └──────────┘
```

**Configuration:**
```bash
# orchestrator.env
ORCHESTRATOR_HOST=10.0.0.10
ORCHESTRATOR_PORT=8000
RED_AGENT_URL=http://10.0.0.11:8000
BLUE_AGENT_URL=http://10.0.0.12:8000

# red-agent.env
AGENT_TYPE=red
ORCHESTRATOR_URL=http://10.0.0.10:8000
AGENT_HOST=10.0.0.11
AGENT_PORT=8000

# blue-agent.env
AGENT_TYPE=blue
ORCHESTRATOR_URL=http://10.0.0.10:8000
AGENT_HOST=10.0.0.12
AGENT_PORT=8000
```

## 4. Tool Execution Framework

### 4.1 Remote Tool Executor

```python
# src/purple_team_gpt/services/common/executor/remote_tool_runner.py

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    duration_ms: float = 0
    tool_name: str = ""
    command: str = ""


class RemoteToolRunner:
    """Executes security tools locally, reports to orchestrator.
    
    Designed to run on the agent's host system with direct access
    to security tools and target networks.
    """
    
    # Tool categories
    RED_TOOLS = {
        "nmap", "nikto", "gobuster", "sqlmap", "curl", "dig",
        "whatweb", "ncrack", "hydra", "whois", "nbtscan",
        "enum4linux", "smbclient", "rpcclient", "ldapsearch",
    }
    
    BLUE_TOOLS = {
        "log_analyzer", "firewall_manager", "process_monitor",
        "file_integrity", "service_manager", "netstat_analyzer",
        "user_auditor", "patch_manager", "backup_manager",
        "iptables", "ufw", "systemctl", "journalctl",
    }
    
    DESTRUCTIVE_PATTERNS = [
        "rm -rf /",
        "dd if=/dev/zero",
        "mkfs",
        ":(){ :|:& };:",
        "chmod 777 /",
        "> /dev/sd",
    ]
    
    def __init__(
        self,
        agent_type: str,
        safe_mode: bool = True,
        default_timeout: int = 300,
        allowed_tools: Optional[set] = None,
    ):
        self.agent_type = agent_type
        self.safe_mode = safe_mode
        self.default_timeout = default_timeout
        self.allowed_tools = allowed_tools or (
            self.RED_TOOLS if agent_type == "red" else self.BLUE_TOOLS
        )
        self._execution_log: list = []
    
    def validate_command(self, command: str, tool_name: str) -> tuple[bool, str]:
        """Validate command for safety and compliance."""
        
        if not command:
            return False, "Empty command"
        
        # Check for destructive patterns
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if pattern in command.lower():
                return False, f"Destructive pattern blocked: {pattern}"
        
        # Check allowed tools
        tool_base = tool_name.split()[0] if tool_name else ""
        if tool_base and tool_base not in self.allowed_tools:
            logger.warning(f"Tool '{tool_base}' not in allowed list")
        
        return True, ""
    
    async def execute(
        self,
        tool_name: str,
        command: str,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """Execute a tool command locally."""
        
        # Validate
        is_valid, error_msg = self.validate_command(command, tool_name)
        if not is_valid:
            return ToolResult(
                success=False,
                output="",
                error=error_msg,
                tool_name=tool_name,
                command=command,
            )
        
        timeout = timeout or self.default_timeout
        start_time = datetime.utcnow()
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout}s",
                    tool_name=tool_name,
                    command=command,
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )
            
            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")
            
            full_output = output
            if error_output and not output:
                full_output = error_output
            elif error_output:
                full_output = f"{output}\n{error_output}"
            
            result = ToolResult(
                success=process.returncode == 0,
                output=full_output,
                error=error_output if process.returncode != 0 else None,
                return_code=process.returncode or 0,
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                tool_name=tool_name,
                command=command,
            )
            
            # Log execution
            self._execution_log.append({
                "tool": tool_name,
                "command": command,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "timestamp": start_time.isoformat(),
            })
            
            return result
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                tool_name=tool_name,
                command=command,
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )
    
    def get_execution_log(self) -> list:
        """Get list of all tool executions."""
        return self._execution_log.copy()
    
    def clear_log(self) -> None:
        """Clear execution log."""
        self._execution_log.clear()
```

### 4.2 Tool Proxy for Orchestrator

```python
# src/purple_team_gpt/services/common/executor/tool_proxy.py

import aiohttp
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionRequest:
    tool_name: str
    command: str
    timeout: int = 300
    safe_mode: bool = True
    session_id: Optional[str] = None


class ToolProxy:
    """Proxy to execute tools on remote agent services.
    
    Used by orchestrator to route tool execution requests
    to the appropriate agent service.
    """
    
    def __init__(self, agent_urls: dict):
        """Initialize with agent service URLs.
        
        Args:
            agent_urls: Dict mapping agent_id to base URL
                       e.g., {"red-1": "http://10.0.0.11:8000"}
        """
        self.agent_urls = agent_urls
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def execute_on_agent(
        self,
        agent_id: str,
        request: ToolExecutionRequest,
    ) -> dict:
        """Execute a tool on a specific agent.
        
        Args:
            agent_id: ID of the agent to execute on
            request: Tool execution request
            
        Returns:
            Execution result dict
        """
        if agent_id not in self.agent_urls:
            return {
                "success": False,
                "error": f"Unknown agent: {agent_id}",
            }
        
        url = f"{self.agent_urls[agent_id]}/api/v1/execute"
        session = await self.get_session()
        
        try:
            async with session.post(url, json={
                "tool_name": request.tool_name,
                "command": request.command,
                "timeout": request.timeout,
                "safe_mode": request.safe_mode,
            }) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "success": False,
                        "error": f"Agent returned {response.status}",
                    }
        
        except aiohttp.ClientError as e:
            logger.error(f"Failed to reach agent {agent_id}: {e}")
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}",
            }
    
    async def close(self):
        if self._session:
            await self._session.close()
```

## 5. Security Considerations

### 5.1 Authentication & Authorization

```python
# src/purple_team_gpt/services/common/auth.py

import hashlib
import secrets
import time
from typing import Optional
from fastapi import Header, HTTPException, status
from pydantic import BaseModel


class AgentCredentials(BaseModel):
    agent_id: str
    api_key: str
    roles: list[str] = ["agent"]


class AuthManager:
    """Manages authentication for distributed agents."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self._registered_agents: dict[str, AgentCredentials] = {}
        self._api_keys: dict[str, str] = {}  # api_key -> agent_id
    
    def generate_api_key(self) -> str:
        """Generate a secure API key."""
        return secrets.token_urlsafe(32)
    
    def register_agent(
        self,
        agent_id: str,
        roles: Optional[list] = None,
    ) -> str:
        """Register an agent and return its API key."""
        api_key = self.generate_api_key()
        
        self._registered_agents[agent_id] = AgentCredentials(
            agent_id=agent_id,
            api_key=api_key,
            roles=roles or ["agent"],
        )
        self._api_keys[api_key] = agent_id
        
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return agent_id."""
        return self._api_keys.get(api_key)
    
    def verify_request_signature(
        self,
        agent_id: str,
        timestamp: str,
        signature: str,
        payload: str,
    ) -> bool:
        """Verify request signature (HMAC-based)."""
        if agent_id not in self._registered_agents:
            return False
        
        # Prevent replay attacks (5 minute window)
        ts = float(timestamp)
        if abs(time.time() - ts) > 300:
            return False
        
        agent = self._registered_agents[agent_id]
        expected = hashlib.sha256(
            f"{agent.api_key}:{timestamp}:{payload}".encode()
        ).hexdigest()
        
        return secrets.compare_digest(signature, expected)


# FastAPI dependency
async def verify_agent(
    x_api_key: str = Header(...),
    auth_manager: AuthManager = None,  # Inject via dependency
) -> str:
    """Verify agent authentication."""
    agent_id = auth_manager.verify_api_key(x_api_key)
    if not agent_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return agent_id
```

### 5.2 Network Security

```python
# Security recommendations for deployment

# 1. TLS/SSL Configuration
"""
All inter-service communication should use TLS:
- Use Let's Encrypt for public deployments
- Self-signed certs for internal networks
- Mutual TLS (mTLS) for agent authentication
"""

# 2. Network Isolation
"""
- Orchestrator on management network only
- Red Agent can reach target network
- Blue Agent monitors target network
- No direct Red <-> Blue communication
"""

# 3. Firewall Rules
"""
Orchestrator:
  - Allow: 8000/tcp (API)
  - Allow: Outbound to agents

Red Agent:
  - Allow: 8000/tcp (from orchestrator only)
  - Allow: Outbound to target network
  - Allow: Outbound to orchestrator

Blue Agent:
  - Allow: 8000/tcp (from orchestrator only)
  - Allow: Outbound to orchestrator
"""

# 4. Rate Limiting
"""
Implement rate limiting on:
- Commands per session
- Tool executions per minute
- API requests per second
"""
```

### 5.3 Audit Logging

```python
# src/purple_team_gpt/services/common/audit.py

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditLogger:
    """Comprehensive audit logging for distributed operations."""
    
    def __init__(self, log_dir: str = "./logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_event(
        self,
        event_type: str,
        agent_id: str,
        session_id: Optional[str],
        details: Dict[str, Any],
        severity: str = "info",
    ):
        """Log an audit event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "session_id": session_id,
            "severity": severity,
            "details": details,
        }
        
        # Write to daily log file
        log_file = self.log_dir / f"audit_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
        
        # Also log to standard logger
        log_msg = f"[{event_type}] {agent_id}: {details}"
        if severity == "critical":
            logger.critical(log_msg)
        elif severity == "high":
            logger.error(log_msg)
        elif severity == "medium":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def log_tool_execution(
        self,
        agent_id: str,
        session_id: str,
        tool_name: str,
        command: str,
        success: bool,
        duration_ms: float,
    ):
        """Log a tool execution event."""
        self.log_event(
            event_type="tool_execution",
            agent_id=agent_id,
            session_id=session_id,
            severity="high" if not success else "info",
            details={
                "tool": tool_name,
                "command": command[:200],  # Truncate for security
                "success": success,
                "duration_ms": duration_ms,
            },
        )
    
    def log_command(
        self,
        source: str,
        target: str,
        command_type: str,
        payload: Dict[str, Any],
    ):
        """Log a command sent between services."""
        self.log_event(
            event_type="command",
            agent_id=source,
            session_id=payload.get("session_id"),
            severity="info",
            details={
                "target": target,
                "command_type": command_type,
                "payload_size": len(str(payload)),
            },
        )
```

## 6. Implementation Roadmap

### Phase 1: Service Skeleton (Week 1-2)
- [ ] Create service directory structure
- [ ] Implement base FastAPI services
- [ ] Add health/status endpoints
- [ ] Create Dockerfiles for each service

### Phase 2: Communication Layer (Week 2-3)
- [ ] Implement message protocol
- [ ] Add WebSocket event streaming
- [ ] Create agent registry
- [ ] Build orchestrator routing

### Phase 3: Tool Execution (Week 3-4)
- [ ] Port tool runner to services
- [ ] Add tool proxy to orchestrator
- [ ] Test remote execution
- [ ] Add execution logging

### Phase 4: Security Hardening (Week 4-5)
- [ ] Implement API key auth
- [ ] Add request signing
- [ ] Configure TLS
- [ ] Set up audit logging

### Phase 5: Deployment (Week 5-6)
- [ ] Docker Compose setup
- [ ] Kubernetes manifests
- [ ] CI/CD pipeline
- [ ] Documentation

## 7. Configuration Reference

### Environment Variables

```bash
# Orchestrator Service
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000
SECRET_KEY=your-secret-key-here
AUTH_REQUIRED=true

# LLM Configuration (shared)
LLM_DEFAULT_PROVIDER=openai
LLM_DEFAULT_MODEL=gpt-4o
LLM_OPENAI_API_KEY=sk-...

# Vector Store
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_PERSIST_DIR=/data/chromadb

# Agent Service (Red/Blue)
AGENT_TYPE=red  # or blue
AGENT_ID=red-agent-1
ORCHESTRATOR_URL=http://orchestrator:8000
AGENT_HOST=0.0.0.0
AGENT_PORT=8000
API_KEY=generated-key-here

# Tool Execution
SAFE_MODE=true
TOOL_TIMEOUT=300
ALLOWED_TOOLS=nmap,nikto,curl
```

## 8. Monitoring & Observability

### Metrics Collection

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'orchestrator'
    static_configs:
      - targets: ['orchestrator:8000']
  
  - job_name: 'red-agent'
    static_configs:
      - targets: ['red-agent:8000']
  
  - job_name: 'blue-agent'
    static_configs:
      - targets: ['blue-agent:8000']
```

### Dashboard Metrics

- Active sessions count
- Agent health status
- Tool execution rate
- Error rate by agent
- Command latency
- WebSocket connections
- Memory/CPU per service