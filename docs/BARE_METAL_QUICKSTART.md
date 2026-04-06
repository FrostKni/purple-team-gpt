# Purple Team GPT - Bare Metal Quick Start

## System Setup

### Network Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NETWORK LAYOUT                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                              Management Network (10.0.0.0/24)
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   │                   ▼
        ┌───────────────────┐          │          ┌───────────────────┐
        │ RED AGENT         │          │          │ BLUE AGENT        │
        │ (Attacker System) │          │          │ (Defender System) │
        │                   │          │          │                   │
        │ Kali Linux 2024   │          │          │ Ubuntu Server 22.04
        │ IP: 10.0.0.20     │          │          │ IP: 10.0.0.30     │
        └─────────┬─────────┘          │          └─────────┬─────────┘
                  │                    │                    │
                  │                    ▼                    │
                  │        ┌───────────────────┐            │
                  │        │ ORCHESTRATOR      │            │
                  │        │ (Command Center)  │            │
                  │        │                   │            │
                  │        │ Ubuntu Server 22.04           │
                  │        │ IP: 10.0.0.10     │            │
                  │        └───────────────────┘            │
                  │                                         │
                  └──────────────────┬──────────────────────┘
                                     │
                              Target Network
                              (Assessment Scope)
```

## Step-by-Step Installation

### Step 1: Orchestrator Setup (10.0.0.10)

```bash
# SSH to orchestrator server
ssh root@10.0.0.10

# Clone repository
git clone https://github.com/your-org/purple-team-gpt.git
cd purple-team-gpt

# Run installation
./scripts/install-orchestrator.sh

# Edit configuration
nano /etc/purple-team-gpt/environment
# Add your OpenAI API key
# LLM_OPENAI_API_KEY=sk-your-key

# Edit orchestrator config
nano /etc/purple-team-gpt/orchestrator.yaml
# Set agent IPs

# Start service
systemctl start purple-team-orchestrator
systemctl status purple-team-orchestrator
```

### Step 2: Red Agent Setup (10.0.0.20)

```bash
# SSH to attacker machine (Kali Linux)
ssh root@10.0.0.20

# Clone repository
git clone https://github.com/your-org/purple-team-gpt.git
cd purple-team-gpt

# Run installation
./scripts/install-red-agent.sh --orchestrator 10.0.0.10:8000

# Save the API key shown at the end!
# Example: Agent ID: red-agent-1
#          API Key: a1b2c3d4e5f6...

# Edit allowed targets
nano /etc/purple-team-gpt/red-agent.yaml
# Add your target network ranges

# Start service
systemctl start purple-team-red-agent
systemctl status purple-team-red-agent
```

### Step 3: Blue Agent Setup (10.0.0.30)

```bash
# SSH to defender machine (Ubuntu Server)
ssh root@10.0.0.30

# Clone repository
git clone https://github.com/your-org/purple-team-gpt.git
cd purple-team-gpt

# Run installation
./scripts/install-blue-agent.sh --orchestrator 10.0.0.10:8000

# Save the API key shown at the end!

# Edit monitoring config
nano /etc/purple-team-gpt/blue-agent.yaml
# Add log paths to monitor

# Start service
systemctl start purple-team-blue-agent
systemctl status purple-team-blue-agent
```

### Step 4: Register Agents on Orchestrator

```bash
# On orchestrator server
nano /etc/purple-team-gpt/orchestrator.yaml

# Add agent configurations:
```

```yaml
agents:
  red:
    - id: red-agent-1
      url: http://10.0.0.20:8000
      api_key: RED_AGENT_API_KEY  # From step 2
  blue:
    - id: blue-agent-1
      url: http://10.0.0.30:8000
      api_key: BLUE_AGENT_API_KEY  # From step 3
```

```bash
# Restart orchestrator
systemctl restart purple-team-orchestrator
```

### Step 5: Verify Connectivity

```bash
# On orchestrator, check agent registration
curl http://localhost:8000/api/v1/agents

# Check red agent health
curl http://10.0.0.20:8000/health

# Check blue agent health
curl http://10.0.0.30:8000/health
```

## Running a Simulation

### Via API

```bash
# Create session
SESSION=$(curl -s -X POST http://10.0.0.10:8000/api/v1/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "target": "192.168.1.100",
    "attack_type": "reconnaissance",
    "red_agent_id": "red-agent-1",
    "blue_agent_id": "blue-agent-1"
  }' | jq -r '.id')

echo "Session ID: $SESSION"

# Start simulation
curl -X POST http://10.0.0.10:8000/api/v1/sessions/$SESSION/start

# Watch logs
curl http://10.0.0.10:8000/api/v1/sessions/$SESSION/logs
```

### Via WebSocket

```python
import asyncio
import websockets
import json

async def watch_session(session_id):
    uri = f"ws://10.0.0.10:8000/ws/session/{session_id}"
    async with websockets.connect(uri) as ws:
        while True:
            data = await ws.recv()
            event = json.loads(data)
            print(f"[{event['agent']}] {event['event_type']}: {event['data']}")

# Run
asyncio.run(watch_session("your-session-id"))
```

## Tool Management

### Check Tool Status

```bash
# On red agent
curl http://10.0.0.20:8000/api/v1/tools/status

# On blue agent
curl http://10.0.0.30:8000/api/v1/tools/status
```

### Install Missing Tools

```bash
# Via API
curl -X POST http://10.0.0.20:8000/api/v1/tools/install \
  -H "Content-Type: application/json" \
  -d '{"tool": "nuclei"}'
```

### Tools auto-install

The agents automatically install missing tools when needed. The Tool Manager:
1. Checks if tool is installed
2. If missing, runs the install command
3. Verifies installation
4. Reports status to orchestrator

## Logs and Monitoring

### Service Logs

```bash
# Orchestrator logs
journalctl -u purple-team-orchestrator -f

# Red agent logs
journalctl -u purple-team-red-agent -f

# Blue agent logs
journalctl -u purple-team-blue-agent -f
```

### Log Files

```bash
# Orchestrator
tail -f /var/log/purple-team-gpt/audit.log

# Red Agent
tail -f /var/log/purple-team-gpt/red-agent.log

# Blue Agent
tail -f /var/log/purple-team-gpt/blue-agent.log
```

## Troubleshooting

### Agent Not Registering

```bash
# Check network connectivity
ping 10.0.0.10

# Check orchestrator is running
curl http://10.0.0.10:8000/health

# Check API key in config
cat /etc/purple-team-gpt/environment | grep API_KEY

# Check service logs
journalctl -u purple-team-red-agent -n 50
```

### Tools Not Installing

```bash
# Check if apt is working
apt update

# Check pip
pip3 --version

# Install tool manually
apt install nmap

# Check tool status
which nmap
nmap --version
```

### Permission Denied

```bash
# Check sudoers
cat /etc/sudoers.d/purple-team-*

# Check service user
id purple-team-red

# Test sudo
sudo -u purple-team-red sudo whoami
```

## Security Checklist

- [ ] Change default SECRET_KEY in all configs
- [ ] Set unique API keys for each agent
- [ ] Configure allowed_targets in red agent config
- [ ] Review safe_mode settings
- [ ] Enable TLS for production
- [ ] Set up firewall rules
- [ ] Configure log rotation
- [ ] Set up monitoring alerts

## Production Hardening

### Enable TLS

```bash
# Generate certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/purple-team-gpt/server.key \
  -out /etc/purple-team-gpt/server.crt

# Update configs to use https://
```

### Firewall Rules

```bash
# On orchestrator
ufw allow 8000/tcp  # API
ufw allow from 10.0.0.0/24  # Agent network
ufw enable

# On red agent
ufw allow from 10.0.0.10  # Orchestrator only
ufw enable
```

### Log Rotation

```bash
cat > /etc/logrotate.d/purple-team-gpt << EOF
/var/log/purple-team-gpt/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 purple-team-orchestrator purple-team-orchestrator
}
EOF
```