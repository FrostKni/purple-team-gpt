# Purple Team GPT - Architecture Design Document

## Executive Summary

Purple Team GPT is an autonomous cybersecurity simulation framework that implements a continuous "Cat and Mouse" game between offensive (Red) and defensive (Blue) AI agents. The system uses a multi-agent LLM architecture with real-time coordination, adaptive learning via RAG, and human-in-the-loop feedback for continuous improvement.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Deployment | Docker containers | Cross-platform, isolated environment, reproducible |
| Agent Coordination | Simultaneous parallel execution | Realistic attack/defense simulation |
| LLM Strategy | Multi-provider with failover | Reliability, cost optimization, flexibility |
| UI | Web UI (FastAPI + React) | Modern, responsive, accessible from any device |
| Memory | Full RAG with fine-tuning export | Adaptive learning, knowledge retention |
| MVP Scope | Core agents + UI + 3-5 tools each | Functional but manageable initial release |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PURPLE TEAM GPT                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        WEB UI (React)                                │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │   Attack     │  │   Defense    │  │  Feedback    │              │    │
│  │  │  Dashboard   │  │  Dashboard   │  │   Portal     │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FASTAPI BACKEND                                   │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │   REST API   │  │  WebSocket   │  │   Auth &     │              │    │
│  │  │   Endpoints  │  │   Manager    │  │   Sessions   │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    AGENT COORDINATION LAYER                          │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │                    Purple Orchestrator                        │   │    │
│  │  │  - Session Management  - Turn Coordination  - State Sync     │   │    │
│  │  └──────────────────────────────────────────────────────────────┘   │    │
│  │            │                              │                          │    │
│  │            ▼                              ▼                          │    │
│  │  ┌──────────────────┐          ┌──────────────────┐                │    │
│  │  │   RED AGENT      │          │   BLUE AGENT     │                │    │
│  │  │  (Offensive)     │          │  (Defensive)     │                │    │
│  │  │  - Recon         │◄────────►│  - Detection     │                │    │
│  │  │  - Exploit       │  Events  │  - Response      │                │    │
│  │  │  - Post-Exploit  │          │  - Recovery      │                │    │
│  │  └──────────────────┘          └──────────────────┘                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      CORE SERVICES                                   │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │  LLM Engine  │  │  RAG Pipeline │  │  Tool Runner │              │    │
│  │  │ (Multi-LLM)  │  │ (ChromaDB)   │  │ (Executor)   │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │ Feedback DB  │  │ Embedding    │  │ Fine-tuning  │              │    │
│  │  │ (SQLite)     │  │ Engine       │  │ Export       │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    TOOL ARSENALS                                     │    │
│  │  ┌────────────────────────────┐  ┌────────────────────────────┐    │    │
│  │  │     RED ARSENAL            │  │     BLUE ARSENAL           │    │    │
│  │  │  - nmap scanner            │  │  - firewall_manager        │    │    │
│  │  │  - sqlmap injector         │  │  - log_monitor             │    │    │
│  │  │  - hydra brute             │  │  - process_watcher         │    │    │
│  │  │  - nikto web scanner       │  │  - file_integrity          │    │    │
│  │  │  - gobuster dir brute      │  │  - service_manager         │    │    │
│  │  └────────────────────────────┘  └────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. LLM Engine (Multi-Provider)

```python
class LLMEngine:
    """Multi-provider LLM with automatic failover."""
    
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "groq": GroqProvider,
        "ollama": OllamaProvider,
        "deepseek": DeepSeekProvider,
    }
    
    features:
        - Automatic failover on rate limits/errors
        - Streaming responses
        - Token counting and cost tracking
        - Provider health monitoring
        - Configurable model selection per agent
```

### 2. RAG Pipeline

```python
class RAGPipeline:
    """Retrieval-Augmented Generation for adaptive learning."""
    
    components:
        - EmbeddingEngine: text-embedding-3-small / all-MiniLM-L6-v2
        - VectorStore: ChromaDB (persistent)
        - Retriever: Similarity search with metadata filtering
        - Indexer: Automatic indexing of interactions
    
    collections:
        - attack_patterns: Successful attack vectors
        - defense_patterns: Effective defense strategies
        - feedback_store: Human feedback entries
        - session_logs: Complete interaction history
```

### 3. Red Agent (Offensive)

```python
class RedAgent:
    """Autonomous offensive security agent."""
    
    capabilities:
        - Reconnaissance: nmap, masscan, subfinder
        - Web scanning: nikto, nuclei, gobuster
        - Exploitation: sqlmap, hydra, custom scripts
        - Post-exploitation: Privilege escalation checks
    
    workflow:
        1. Query RAG for similar target patterns
        2. Plan attack strategy
        3. Execute tools sequentially
        4. Analyze results, adapt approach
        5. Report findings to orchestrator
```

### 4. Blue Agent (Defensive)

```python
class BlueAgent:
    """Autonomous defensive security agent."""
    
    capabilities:
        - Detection: Log analysis, anomaly detection
        - Response: Firewall rules, service restarts
        - Recovery: Rollback, patch recommendations
        - Hardening: Security configurations
    
    workflow:
        1. Monitor system state (logs, processes, network)
        2. Query RAG for similar threat patterns
        3. Detect anomalies using LLM reasoning
        4. Execute defense scripts
        5. Report actions to orchestrator
```

### 5. Agent Coordination Layer

```python
class PurpleOrchestrator:
    """Coordinates Red and Blue agents in real-time."""
    
    responsibilities:
        - Session management (create, pause, resume)
        - Event routing between agents
        - State synchronization
        - Conflict resolution
        - Scoring and metrics
    
    coordination_modes:
        - SIMULTANEOUS: Both agents run in parallel
        - TURN_BASED: Alternating execution
        - REACTIVE: Blue responds to Red's actions
    
    events:
        - ATTACK_DETECTED: Red performed action
        - DEFENSE_TRIGGERED: Blue responded
        - FEEDBACK_RECEIVED: Human provided input
        - SESSION_END: Assessment complete
```

### 6. FastAPI Backend

```python
# Endpoints structure
/api/v1/
├── /sessions
│   ├── POST /create          # Create new session
│   ├── GET /{id}             # Get session status
│   ├── POST /{id}/start      # Start agents
│   ├── POST /{id}/stop       # Stop session
│   └── GET /{id}/report      # Get final report
├── /agents
│   ├── GET /red/status       # Red agent status
│   ├── GET /blue/status      # Blue agent status
│   └── POST /feedback        # Submit human feedback
├── /tools
│   ├── GET /                 # List available tools
│   └── POST /execute         # Execute specific tool
└── /ws
    └── /session/{id}         # WebSocket for real-time updates
```

### 7. React Web UI

```
/src
├── /components
│   ├── Dashboard/
│   │   ├── AttackDashboard.tsx
│   │   ├── DefenseDashboard.tsx
│   │   └── MetricsPanel.tsx
│   ├── Agents/
│   │   ├── AgentStatus.tsx
│   │   ├── AgentLogs.tsx
│   │   └── AgentControls.tsx
│   └── Feedback/
│       ├── FeedbackForm.tsx
│       └── RatingComponent.tsx
├── /hooks
│   ├── useWebSocket.ts
│   └── useSession.ts
└── /services
    └── api.ts
```

---

## Data Flow

### Attack Flow

```
User → UI → API → Orchestrator → Red Agent
                                    │
                                    ▼
                               Query RAG
                                    │
                                    ▼
                            Select Tools
                                    │
                                    ▼
                           Execute Attack
                                    │
                                    ▼
                         Report to Orchestrator
                                    │
                                    ▼
                           Broadcast to Blue
                                    │
                                    ▼
                        Store in Vector DB
                                    │
                                    ▼
                            Update UI (WebSocket)
```

### Defense Flow

```
Blue Agent ← Event from Orchestrator
    │
    ▼
Query RAG for similar threats
    │
    ▼
Analyze logs/detect anomaly
    │
    ▼
Generate defense action
    │
    ▼
Execute defense script
    │
    ▼
Report to Orchestrator
    │
    ▼
Store result in Vector DB
    │
    ▼
Update UI (WebSocket)
```

### Learning Flow

```
Session Complete
    │
    ▼
Extract interactions
    │
    ▼
Generate embeddings
    │
    ▼
Store in ChromaDB
    │
    ▼
Human feedback collected
    │
    ▼
Rate interaction quality
    │
    ▼
5-star rated → JSONL export for fine-tuning
```

---

## Tool Arsenal

### Red Arsenal (Offensive)

| Tool | Purpose | Risk Level |
|------|---------|------------|
| nmap | Port scanning, service detection | Low |
| nikto | Web vulnerability scanning | Low |
| gobuster | Directory brute forcing | Medium |
| sqlmap | SQL injection testing | High |
| hydra | Credential brute forcing | High |

### Blue Arsenal (Defensive)

| Tool | Purpose | Risk Level |
|------|---------|------------|
| firewall_manager | iptables rules management | Medium |
| log_monitor | Real-time log analysis | Low |
| process_watcher | Monitor running processes | Low |
| file_integrity | FIM for critical files | Low |
| service_manager | Start/stop/restart services | Medium |

---

## Database Schema

### SQLite (Feedback & Sessions)

```sql
-- Sessions
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    target TEXT NOT NULL,
    scope TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Feedback
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    agent_type TEXT,  -- 'red' or 'blue'
    interaction_id TEXT,
    rating INTEGER,   -- 1-5 stars
    comment TEXT,
    timestamp TIMESTAMP
);

-- Findings
CREATE TABLE findings (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    agent_type TEXT,
    title TEXT,
    severity TEXT,
    description TEXT,
    evidence TEXT,
    recommendation TEXT,
    timestamp TIMESTAMP
);
```

### ChromaDB Collections

```python
collections = {
    "attack_patterns": {
        "metadata": ["target_type", "attack_type", "success", "timestamp"]
    },
    "defense_patterns": {
        "metadata": ["threat_type", "response_type", "effectiveness", "timestamp"]
    },
    "feedback_store": {
        "metadata": ["session_id", "agent_type", "rating", "timestamp"]
    },
    "session_logs": {
        "metadata": ["session_id", "agent_type", "action", "timestamp"]
    }
}
```

---

## Docker Configuration

```yaml
# docker-compose.yml
services:
  backend:
    build: ./src/backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
  
  frontend:
    build: ./src/frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
  
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/data

volumes:
  chromadb_data:
```

---

## Security Considerations

1. **API Key Storage**: Environment variables, never in code
2. **Target Authorization**: Require explicit scope confirmation
3. **Tool Sandboxing**: Run tools in isolated containers
4. **Rate Limiting**: Prevent abuse of LLM APIs
5. **Audit Logging**: Complete action history for compliance
6. **Input Validation**: Sanitize all user inputs
7. **Safe Mode**: Default to non-destructive operations

---

## Performance Targets

| Metric | Target |
|--------|--------|
| LLM Response Time | < 3s (streaming) |
| Tool Execution | < 30s (typical) |
| WebSocket Latency | < 100ms |
| RAG Query Time | < 500ms |
| Session Startup | < 5s |

---

## Extensibility

### Adding New LLM Provider

```python
# src/core/llm/providers/new_provider.py
class NewProvider(BaseProvider):
    def __init__(self, api_key: str, **kwargs):
        ...
    
    async def chat(self, messages: list, **kwargs) -> str:
        ...
    
    async def stream(self, messages: list, **kwargs) -> AsyncIterator[str]:
        ...
```

### Adding New Tool

```python
# scripts/red_arsenal/new_tool.py
from tools.base import BaseTool

class NewTool(BaseTool):
    name = "new_tool"
    description = "Description for LLM"
    risk_level = "medium"
    
    def execute(self, target: str, **kwargs) -> ToolResult:
        ...
```

### Adding New Agent

```python
# src/agents/custom_agent.py
class CustomAgent(BaseAgent):
    role = "custom"
    
    async def process_event(self, event: Event) -> list[Action]:
        ...
```

---

## File Structure

```
purple-team-gpt/
├── config/
│   ├── settings.yaml           # Main configuration
│   ├── tools_registry.json     # Tool definitions
│   └── prompts/                # Agent prompts
│       ├── red_agent.yaml
│       └── blue_agent.yaml
├── src/
│   ├── backend/
│   │   ├── main.py             # FastAPI app
│   │   ├── routers/
│   │   ├── models/
│   │   └── services/
│   ├── frontend/
│   │   ├── package.json
│   │   ├── src/
│   │   └── public/
│   ├── agents/
│   │   ├── base.py
│   │   ├── red_agent.py
│   │   └── blue_agent.py
│   ├── core/
│   │   ├── llm/
│   │   ├── rag/
│   │   └── orchestrator.py
│   └── tools/
│       ├── base.py
│       └── runner.py
├── scripts/
│   ├── red_arsenal/
│   │   ├── nmap_scanner.py
│   │   ├── nikto_scanner.py
│   │   └── ...
│   └── blue_arsenal/
│       ├── firewall_manager.py
│       ├── log_monitor.py
│       └── ...
├── tests/
│   ├── test_agents.py
│   ├── test_llm.py
│   └── test_tools.py
├── data/                       # Persistent data
│   ├── chromadb/
│   ├── sessions.db
│   └── exports/
├── docs/
│   ├── ARCHITECTURE.md
│   └── API.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```