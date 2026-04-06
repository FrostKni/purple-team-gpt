# Docker Experimentation Guide

This guide explains how to run Purple Team GPT in Docker containers for experimentation and testing.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DOCKER EXPERIMENTATION ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────────────┐
                            │   Your Machine      │
                            │   (Docker Host)     │
                            │   Ports:            │
                            │   - 8000 (API)      │
                            │   - 3000 (UI)       │
                            │   - 9090 (Metrics)  │
                            └──────────┬──────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        │  MANAGEMENT NETWORK (10.0.0.0/24)                           │
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   ORCHESTRATOR    │    │    RED AGENT      │    │    BLUE AGENT     │
│   (Ubuntu)        │    │   (Kali Linux)    │    │  (Ubuntu Server)  │
│                   │    │                   │    │                   │
│   IP: 10.0.0.10   │    │   IP: 10.0.0.20   │    │   IP: 10.0.0.30   │
│   Port: 8000      │◄──►│   Port: 8000      │◄──►│   Port: 8000      │
│                   │    │                   │    │                   │
│   • FastAPI       │    │   • 50+ Offensive │    │   • 50+ Defensive │
│   • Coordination  │    │     Tools         │    │     Tools         │
│   • Learning      │    │   • Nmap, SQLMap  │    │   • Suricata,     │
│   • Feedback      │    │   • Metasploit    │    │     Fail2ban      │
│                   │    │   • CrackMapExec  │    │   • ClamAV, AIDE  │
└────────┬──────────┘    └────────┬──────────┘    └────────┬──────────┘
         │                        │                        │
         │         ┌──────────────┴──────────────┐        │
         │         │    ATTACK NETWORK           │        │
         │         │    (192.168.100.0/24)       │        │
         │         └──────────────┬──────────────┘        │
         │                        │                        │
         │                        ▼                        │
         │              ┌───────────────────┐             │
         │              │  TARGET NETWORK   │             │
         │              │  (DVWA, etc.)     │             │
         │              │  IP: 192.168.100.x│             │
         │              └───────────────────┘             │
         │                                                  │
         ▼                                                  ▼
┌───────────────────┐                            ┌───────────────────┐
│    CHROMADB       │                            │      REDIS        │
│  (Vector Memory)  │                            │  (Message Queue)  │
│   IP: 10.0.0.40   │                            │   IP: 10.0.0.50   │
└───────────────────┘                            └───────────────────┘
```

## Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- At least 16GB RAM
- 50GB+ disk space

```bash
# Check Docker version
docker --version
docker compose version
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

Required configuration:
```env
# LLM API Keys (at least one required)
LLM_OPENAI_API_KEY=sk-...
LLM_ANTHROPIC_API_KEY=sk-ant-...

# Security
SECRET_KEY=your-random-secret-key-here
```

### 3. Build Images

```bash
# Make script executable
chmod +x docker-start.sh

# Build all images (this takes 15-30 minutes)
./docker-start.sh build
```

### 4. Start Services

```bash
# Start all services
./docker-start.sh up

# Check status
./docker-start.sh status
```

### 5. Access the System

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8000 | Orchestrator API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Red Agent | http://localhost:8001 | Red Agent API |
| Blue Agent | http://localhost:8002 | Blue Agent API |
| ChromaDB | http://localhost:8003 | Vector DB UI |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3001 | Dashboards |

## Container Details

### Red Agent (Kali Linux)

The Red Agent runs in a full Kali Linux container with 50+ offensive tools:

**Scanning & Reconnaissance:**
- nmap, masscan, rustscan
- nikto, nuclei, whatweb
- gobuster, ffuf, feroxbuster
- subfinder, amass, httpx

**Exploitation:**
- metasploit-framework
- sqlmap
- crackmapexec
- impacket

**Password Attacks:**
- hydra, medusa, ncrack
- john, hashcat
- wordlists (rockyou, seclists)

**Wireless:**
- aircrack-ng
- wifite
- reaver

**Post-Exploitation:**
- empire
- sliver
- proxychains

**Access Red Agent:**
```bash
./docker-start.sh shell red-agent

# Inside container:
nmap --version
msfconsole
sqlmap --version
```

### Blue Agent (Ubuntu Server)

The Blue Agent runs in Ubuntu Server with 50+ defensive tools:

**Firewall & Network:**
- iptables, ufw, nftables
- suricata, zeek, snort
- fail2ban

**Host-Based Security:**
- aide (file integrity)
- rkhunter, chkrootkit
- clamav
- auditd

**Monitoring:**
- tcpdump, tshark
- htop, iotop, nethogs
- prometheus-node-exporter

**Forensics:**
- volatility, volatility3
- sleuthkit, autopsy
- foremost, scalpel

**Access Blue Agent:**
```bash
./docker-start.sh shell blue-agent

# Inside container:
suricata --build-info
clamscan --version
aide --version
```

### Orchestrator

The central coordination service:

**Features:**
- FastAPI REST API
- WebSocket for real-time events
- LLM integration (OpenAI, Anthropic, local)
- Vector memory (ChromaDB)
- Feedback collection

**Access Orchestrator:**
```bash
./docker-start.sh shell orchestrator

# Test API:
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/agents
```

## Running Simulations

### Example: Web Application Scan

```bash
# Create a simulation
curl -X POST http://localhost:8000/api/v1/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DVWA Scan",
    "target": "192.168.100.100",
    "attack_type": "web_scan",
    "red_agent_id": "red-agent-kali-01",
    "blue_agent_id": "blue-agent-ubuntu-01"
  }'

# Monitor progress
curl http://localhost:8000/api/v1/simulations/{simulation_id}/status

# Get results
curl http://localhost:8000/api/v1/simulations/{simulation_id}/results
```

### Example: With Python

```python
import httpx

async def run_simulation():
    async with httpx.AsyncClient() as client:
        # Create simulation
        response = await client.post(
            "http://localhost:8000/api/v1/simulations",
            json={
                "name": "Test Scan",
                "target": "192.168.100.100",
                "attack_type": "port_scan"
            }
        )
        sim = response.json()
        print(f"Simulation ID: {sim['id']}")
        
        # WebSocket for real-time updates
        async with client.websocket_connect(
            f"ws://localhost:8000/ws/simulations/{sim['id']}"
        ) as ws:
            while True:
                data = await ws.receive_json()
                print(f"Event: {data['type']} - {data['message']}")
                if data['type'] == 'simulation_complete':
                    break
```

## Adding Target Systems

### DVWA (Damn Vulnerable Web App)

```bash
# Start with vulnerable targets
docker compose -f docker-compose.experiment.yml --profile target up -d dvwa

# Access DVWA
open http://localhost:8080
# Login: admin / password
```

### Custom Targets

```yaml
# Add to docker-compose.experiment.yml
  my-target:
    image: your-vulnerable-app:latest
    networks:
      attack:
        ipv4_address: 192.168.100.200
```

## Monitoring & Debugging

### View Logs

```bash
# All services
./docker-start.sh logs

# Specific service
./docker-start.sh logs red-agent
./docker-start.sh logs blue-agent
./docker-start.sh logs orchestrator
```

### Check Tool Availability

```bash
./docker-start.sh tools
```

### Resource Usage

```bash
docker stats
```

### Health Checks

```bash
./docker-start.sh status
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.experiment.yml logs orchestrator

# Rebuild image
docker compose -f docker-compose.experiment.yml build --no-cache orchestrator
```

### Out of Memory

```bash
# Increase Docker memory limit
# Or reduce concurrent operations
export MAX_CONCURRENT_TASKS=2
```

### Tool Not Found

```bash
# Enter container and install
./docker-start.sh shell red-agent
apt-get update && apt-get install -y tool-name
```

### Network Issues

```bash
# Check network connectivity
docker exec purple-team-red-agent ping -c 3 192.168.100.100

# Inspect networks
docker network ls
docker network inspect purple-team-gpt_attack
```

## Cleanup

```bash
# Stop all services
./docker-start.sh down

# Remove everything (including volumes)
./docker-start.sh clean
```

## Security Notes

⚠️ **WARNING: These containers contain offensive security tools.**

1. **Run in isolated environments only**
2. **Do not expose to the internet**
3. **Only target systems you own/have permission to test**
4. **Safe mode is enabled by default** - disable with `SAFE_MODE=false` for actual attacks
5. **Destructive operations are disabled** - enable with `DESTRUCTIVE_OPERATIONS=true` only when needed

## Next Steps

1. Read the [API Documentation](http://localhost:8000/docs)
2. Try the [examples](../examples/)
3. Customize [tools registry](../config/tools_registry.json)
4. Add your own [attack scripts](../scripts/red_arsenal/)
5. Add your own [defense scripts](../scripts/blue_arsenal/)