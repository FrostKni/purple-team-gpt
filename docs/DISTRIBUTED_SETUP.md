# Distributed Purple Team GPT - Setup Guide

## Quick Start

### Prerequisites

- Docker & Docker Compose
- LLM API Key (OpenAI, Anthropic, or local Ollama)
- Target system(s) for testing

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/your-org/purple-team-gpt.git
cd purple-team-gpt

# Create environment file
cat > .env << 'EOF'
# LLM Configuration
LLM_DEFAULT_PROVIDER=openai
LLM_OPENAI_API_KEY=sk-your-key-here

# Security
SECRET_KEY=$(openssl rand -hex 32)

# Agent Configuration
SAFE_MODE=true
TOOL_TIMEOUT=300
EOF
```

### 2. Start Distributed Services

```bash
cd deploy
docker-compose up -d
```

### 3. Verify Services

```bash
# Check all services are running
docker-compose ps

# Check orchestrator
curl http://localhost:8000/health

# Check red agent
curl http://localhost:8001/health

# Check blue agent
curl http://localhost:8002/health
```

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Orchestrator  │────▶│   Red Agent     │────▶│ Target Network  │
│   (Port 8000)   │     │   (Port 8001)   │     │                 │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         │              ┌─────────────────┐     ┌─────────────────┐
         └─────────────▶│   Blue Agent    │────▶│ System Logs     │
                        │   (Port 8002)   │     │ /var/log, /proc │
                        └─────────────────┘     └─────────────────┘
```

## Deployment Options

### Option 1: Docker Compose (Development)

All services run in Docker containers on the same host:

```bash
cd deploy
docker-compose up -d
```

**Pros**: Quick setup, easy development
**Cons**: Limited network isolation

### Option 2: Separate Docker Hosts (Production)

Deploy each service on separate machines:

#### Orchestrator Host
```bash
docker run -d \
  --name orchestrator \
  -p 8000:8000 \
  -e SECRET_KEY=your-secret \
  -e LLM_OPENAI_API_KEY=your-key \
  purple-team-gpt/orchestrator:latest
```

#### Red Agent Host (Attacker System)
```bash
docker run -d \
  --name red-agent \
  -p 8001:8000 \
  --privileged \
  --cap-add=NET_ADMIN,NET_RAW \
  -e ORCHESTRATOR_URL=http://ORCHESTRATOR_IP:8000 \
  -e SECRET_KEY=your-secret \
  purple-team-gpt/red-agent:latest
```

#### Blue Agent Host (Defender System)
```bash
docker run -d \
  --name blue-agent \
  -p 8002:8000 \
  --privileged \
  -v /var/log:/var/log:ro \
  -v /etc:/etc:ro \
  -e ORCHESTRATOR_URL=http://ORCHESTRATOR_IP:8000 \
  -e SECRET_KEY=your-secret \
  purple-team-gpt/blue-agent:latest
```

### Option 3: Physical/VM Deployment (Air-Gapped)

For isolated environments:

1. **Build packages**:
```bash
pip install build
python -m build
```

2. **Install on each system**:
```bash
# On orchestrator
pip install purple_team_gpt[orchestrator]

# On red agent
pip install purple_team_gpt[red-agent]

# On blue agent
pip install purple_team_gpt[blue-agent]
```

3. **Run services**:
```bash
# Orchestrator
purple-team-orchestrator --host 0.0.0.0 --port 8000

# Red Agent
purple-team-red-agent --orchestrator http://ORCH_IP:8000

# Blue Agent
purple-team-blue-agent --orchestrator http://ORCH_IP:8000
```

## Agent Configuration

### Red Agent Configuration

The Red Agent needs:
- Network access to target systems
- Offensive security tools installed
- Privileged mode for network operations

```yaml
# config/red-agent.yaml
agent:
  type: red
  id: red-agent-1
  
orchestrator:
  url: http://orchestrator:8000
  
tools:
  timeout: 300
  safe_mode: true
  
capabilities:
  - reconnaissance
  - scanning
  - exploitation
  - post-exploitation
```

### Blue Agent Configuration

The Blue Agent needs:
- Access to system logs (`/var/log`)
- Access to system info (`/etc`, `/proc`)
- Privileged mode for defensive operations

```yaml
# config/blue-agent.yaml
agent:
  type: blue
  id: blue-agent-1
  
orchestrator:
  url: http://orchestrator:8000
  
monitoring:
  log_paths:
    - /var/log/auth.log
    - /var/log/syslog
    - /var/log/nginx/access.log
  
response:
  auto_block: false
  firewall: iptables
  
capabilities:
  - detection
  - analysis
  - response
  - recovery
```

## Creating a Simulation Session

### Via API

```bash
# Create session
curl -X POST http://localhost:8000/api/v1/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "target": "192.168.1.100",
    "attack_type": "reconnaissance",
    "red_agent_id": "red-agent-1",
    "blue_agent_id": "blue-agent-1"
  }'

# Start simulation
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/start
```

### Via WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session/{session_id}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`[${data.agent}] ${data.type}: ${data.message}`);
};
```

## Monitoring

### Service Health

```bash
# All services
docker-compose ps

# Service logs
docker-compose logs -f orchestrator
docker-compose logs -f red-agent
docker-compose logs -f blue-agent
```

### Agent Status

```bash
# Red agent status
curl http://localhost:8001/api/v1/status

# Blue agent status
curl http://localhost:8002/api/v1/status
```

## Security Considerations

### 1. Network Segmentation

- Red Agent: Isolated attack network
- Blue Agent: Management network only
- Orchestrator: Both networks

### 2. Authentication

All inter-service communication uses:
- API key authentication
- Request signing
- TLS (recommended for production)

### 3. Authorization

- SAFE_MODE=true: Limits destructive operations
- Tool whitelisting: Only approved tools can run
- Audit logging: All actions logged

## Troubleshooting

### Red Agent Can't Reach Target

```bash
# Check network connectivity
docker exec -it purple-team-red-agent ping TARGET_IP

# Check network mode
docker inspect purple-team-red-agent | grep NetworkMode
```

### Blue Agent Can't Monitor Logs

```bash
# Check volume mounts
docker inspect purple-team-blue-agent | grep -A 5 Mounts

# Test log access
docker exec -it purple-team-blue-agent ls /var/log
```

### Agent Not Registering

```bash
# Check orchestrator connectivity
docker exec -it purple-team-red-agent curl http://orchestrator:8000/health

# Check secret key matches
docker exec -it purple-team-red-agent env | grep SECRET
```

## Next Steps

1. Configure target network access
2. Set up monitoring dashboards
3. Create custom tool scripts
4. Configure alerting rules
5. Set up log forwarding