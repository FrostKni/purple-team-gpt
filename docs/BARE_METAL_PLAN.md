# Purple Team GPT - Bare Metal/VM Deployment Plan

## Vision

Run agents directly on physical systems with full control:
- **Red Agent**: Dedicated attacker machine (Kali Linux recommended)
- **Blue Agent**: Dedicated defender machine (Ubuntu Server/Security Onion)
- **Orchestrator**: Central coordination server
- Agents can self-install missing tools dynamically

## System Requirements

### Orchestrator Server
- Ubuntu 22.04+ or similar Linux
- 4GB RAM minimum
- Python 3.11+
- Network accessible by all agents

### Red Agent Machine (Attacker System)
- Kali Linux 2024+ (recommended) or any Linux with offensive tools
- 8GB RAM minimum
- Python 3.11+
- Network access to target scope
- Root/sudo access for tool execution

### Blue Agent Machine (Defender System)
- Ubuntu Server 22.04+ / Security Onion / Rocky Linux
- 8GB RAM minimum
- Python 3.11+
- Access to system logs, network traffic
- Root/sudo access for defensive operations

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PHYSICAL/VM DEPLOYMENT                          │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────┐
                    │     ORCHESTRATOR SERVER      │
                    │   (Central Command Center)   │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │   Orchestrator API     │  │
                    │  │   - Session Management │  │
                    │  │   - Agent Registry     │  │
                    │  │   - LLM Integration    │  │
                    │  └────────────────────────┘  │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │   Vector Store         │  │
                    │  │   (ChromaDB)           │  │
                    │  └────────────────────────┘  │
                    │                              │
                    │  IP: 10.0.0.10              │
                    │  Port: 8000                 │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │                              │
                    ▼                              ▼
    ┌──────────────────────────────┐  ┌──────────────────────────────┐
    │   RED AGENT MACHINE          │  │   BLUE AGENT MACHINE         │
    │   (Attacker Workstation)     │  │   (Defender Workstation)     │
    │                              │  │                              │
    │  ┌────────────────────────┐  │  │  ┌────────────────────────┐  │
    │  │   Red Agent Service    │  │  │  │   Blue Agent Service   │  │
    │  │   (systemd)            │  │  │  │   (systemd)            │  │
    │  └───────────┬────────────┘  │  │  └───────────┬────────────┘  │
    │              │               │  │              │               │
    │  ┌───────────┴────────────┐  │  │  ┌───────────┴────────────┐  │
    │  │   Tool Manager         │  │  │  │   Tool Manager         │  │
    │  │   - Auto-install       │  │  │  │   - Auto-install       │  │
    │  │   - Version check      │  │  │  │   - Version check      │  │
    │  │   - Update tools       │  │  │  │   - Update tools       │  │
    │  └───────────┬────────────┘  │  │  └───────────┬────────────┘  │
    │              │               │  │              │               │
    │  ┌───────────┴────────────┐  │  │  ┌───────────┴────────────┐  │
    │  │   OFFENSIVE TOOLS      │  │  │  │   DEFENSIVE TOOLS      │  │
    │  │   ┌─────────────────┐  │  │  │  │   ┌─────────────────┐  │  │
    │  │   │ nmap            │  │  │  │  │   │ iptables/ufw    │  │  │
    │  │   │ nikto           │  │  │  │  │   │ fail2ban        │  │  │
    │  │   │ sqlmap          │  │  │  │  │   │ rkhunter        │  │  │
    │  │   │ gobuster        │  │  │  │  │   │ chkrootkit      │  │  │
    │  │   │ hydra           │  │  │  │  │   ├── ossec/wazuh   │  │  │
    │  │   │ metasploit      │  │  │  │  │   ├── suricata      │  │  │
    │  │   │ burpsuite       │  │  │  │  │   ├── zeek/bro      │  │  │
    │  │   │ john            │  │  │  │  │   ├── elk_stack     │  │  │
    │  │   │ hashcat         │  │  │  │  │   │ auditd          │  │  │
    │  │   │ responder       │  │  │  │  │   │ osquery         │  │  │
    │  │   │ impacket        │  │  │  │  │   │ crowdsec        │  │  │
    │  │   │ crackmapexec    │  │  │  │  │   │ clamav          │  │  │
    │  │   └─────────────────┘  │  │  │  │   └─────────────────┘  │  │
    │  └────────────────────────┘  │  │  └────────────────────────┘  │
    │                              │  │                              │
    │  IP: 10.0.0.20              │  │  IP: 10.0.0.30               │
    │  Port: 8000                 │  │  Port: 8000                  │
    │  OS: Kali Linux 2024        │  │  OS: Ubuntu 22.04 Server     │
    └──────────────┬───────────────┘  └──────────────┬───────────────┘
                   │                                  │
                   ▼                                  ▼
        ┌──────────────────┐               ┌──────────────────┐
        │  TARGET NETWORK  │               │  MONITORED HOSTS │
        │  (Assessment     │               │  (Production     │
        │   Scope)         │               │   Systems)       │
        └──────────────────┘               └──────────────────┘
```

## Component Design

### 1. Tool Manager (Auto-Install System)

Each agent includes a Tool Manager that:
- Checks if required tools are installed
- Automatically installs missing tools
- Updates tools when needed
- Reports tool status to orchestrator

```python
class ToolManager:
    """Manages tool installation and updates on the agent system."""
    
    TOOLS = {
        "red": {
            "nmap": {"check": "nmap --version", "install": "apt install -y nmap"},
            "nikto": {"check": "nikto -Version", "install": "apt install -y nikto"},
            "sqlmap": {"check": "sqlmap --version", "install": "apt install -y sqlmap"},
            # ... more tools
        },
        "blue": {
            "iptables": {"check": "iptables --version", "install": "apt install -y iptables"},
            "fail2ban": {"check": "fail2ban-client -V", "install": "apt install -y fail2ban"},
            # ... more tools
        }
    }
    
    async def ensure_tool(self, tool_name: str) -> bool:
        """Ensure tool is installed, install if missing."""
        pass
```

### 2. System Service (systemd)

Each agent runs as a systemd service:
- Auto-starts on boot
- Restarts on failure
- Logs to journald
- Can be managed via systemctl

### 3. Direct System Access

Agents execute commands directly:
- No container isolation
- Full system access
- Root/sudo when needed
- Real tool execution

## Installation Process

### Step 1: Orchestrator Setup

```bash
# On orchestrator server (10.0.0.10)
git clone https://github.com/your-org/purple-team-gpt.git
cd purple-team-gpt

# Install
./scripts/install-orchestrator.sh

# Configure
nano /etc/purple-team-gpt/orchestrator.yaml

# Start service
systemctl enable purple-team-orchestrator
systemctl start purple-team-orchestrator
```

### Step 2: Red Agent Setup

```bash
# On attacker machine (10.0.0.20) - Kali Linux
git clone https://github.com/your-org/purple-team-gpt.git
cd purple-team-gpt

# Install agent
./scripts/install-red-agent.sh --orchestrator 10.0.0.10:8000

# Configure
nano /etc/purple-team-gpt/red-agent.yaml

# Start service
systemctl enable purple-team-red-agent
systemctl start purple-team-red-agent
```

### Step 3: Blue Agent Setup

```bash
# On defender machine (10.0.0.30) - Ubuntu Server
git clone https://github.com/your-org/purple-team-gpt.git
cd purple-team-gpt

# Install agent
./scripts/install-blue-agent.sh --orchestrator 10.0.0.10:8000

# Configure
nano /etc/purple-team-gpt/blue-agent.yaml

# Start service
systemctl enable purple-team-blue-agent
systemctl start purple-team-blue-agent
```

## Communication Flow

```
1. Agent Registration
   ┌─────────────┐                    ┌─────────────┐
   │ Red Agent   │───REGISTER────────▶│Orchestrator │
   │             │◀──ACK + CONFIG─────│             │
   └─────────────┘                    └─────────────┘

2. Tool Status Report
   ┌─────────────┐                    ┌─────────────┐
   │ Red Agent   │───TOOL_STATUS─────▶│Orchestrator │
   │             │    {nmap: ok,      │             │
   │             │     sqlmap: miss}  │             │
   └─────────────┘                    └─────────────┘

3. Session Execution
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │Orchestrator │──▶│ Red Agent   │──▶│   Target    │
   │             │    │ Execute     │    │   System   │
   │             │◀───│ Result      │    │            │
   └─────────────┘  └─────────────┘  └─────────────┘
         │
         │         ┌─────────────┐  ┌─────────────┐
         └────────▶│ Blue Agent  │──▶│  Monitored  │
                   │ Detect      │    │   System    │
                   │ Respond     │    │             │
                   └─────────────┘  └─────────────┘
```

## Security Model

### Authentication
- Pre-shared API keys between orchestrator and agents
- TLS encryption for all communication
- Certificate-based agent authentication

### Authorization
- SAFE_MODE flag for destructive operations
- Tool whitelisting
- Scope restrictions (target IP ranges)

### Audit
- All commands logged
- Tool usage tracked
- Session recordings

## Tool Auto-Install Matrix

### Red Agent Tools (Kali Linux)

| Tool | Category | Install Command |
|------|----------|-----------------|
| nmap | Scanning | `apt install nmap` |
| nikto | Web Scanning | `apt install nikto` |
| sqlmap | SQL Injection | `apt install sqlmap` |
| gobuster | Directory Enum | `apt install gobuster` |
| hydra | Brute Force | `apt install hydra` |
| john | Password Cracking | `apt install john` |
| hashcat | GPU Cracking | `apt install hashcat` |
| metasploit | Exploitation | `curl https://apt.metasploit.com/install.sh \| sh` |
| burpsuite | Web Testing | `apt install burpsuite` |
| responder | LLMNR/NBT-NS | `apt install responder` |
| impacket | SMB/AD Tools | `pip install impacket` |
| crackmapexec | AD Enumeration | `pip install crackmapexec` |
| bloodhound | AD Graph | `apt install bloodhound` |
| nuclei | Vuln Scanning | `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest` |
| ffuf | Fuzzing | `apt install ffuf` |
| amass | OSINT | `apt install amass` |

### Blue Agent Tools (Ubuntu Server)

| Tool | Category | Install Command |
|------|----------|-----------------|
| iptables | Firewall | `apt install iptables` |
| ufw | Firewall Manager | `apt install ufw` |
| fail2ban | Intrusion Prevention | `apt install fail2ban` |
| rkhunter | Rootkit Hunter | `apt install rkhunter` |
| chkrootkit | Rootkit Check | `apt install chkrootkit` |
| suricata | IDS/IPS | `apt install suricata` |
| zeek | Network Analysis | `apt install zeek` |
| osquery | System Monitoring | `apt install osquery` |
| auditd | System Auditing | `apt install auditd` |
| crowdsec | Threat Intelligence | `curl -s https://install.crowdsec.net \| sh` |
| wazuh | HIDS/SIEM | `apt install wazuh-agent` |
| clamav | Antivirus | `apt install clamav` |
| logwatch | Log Analysis | `apt install logwatch` |
| psad | Port Scan Detection | `apt install psad` |
| fwsnort | Snort to iptables | `apt install fwsnort` |

## Configuration Files

### Orchestrator (/etc/purple-team-gpt/orchestrator.yaml)

```yaml
server:
  host: 0.0.0.0
  port: 8000
  
llm:
  provider: openai
  model: gpt-4o
  api_key: ${OPENAI_API_KEY}
  
agents:
  red:
    - id: red-agent-1
      url: http://10.0.0.20:8000
  blue:
    - id: blue-agent-1
      url: http://10.0.0.30:8000
      
security:
  secret_key: ${SECRET_KEY}
  safe_mode: true
  
storage:
  chroma_persist_dir: /var/lib/purple-team-gpt/chromadb
  audit_log: /var/log/purple-team-gpt/audit.log
```

### Red Agent (/etc/purple-team-gpt/red-agent.yaml)

```yaml
agent:
  type: red
  id: red-agent-1
  
orchestrator:
  url: http://10.0.0.10:8000
  api_key: ${AGENT_API_KEY}
  
tools:
  auto_install: true
  update_on_start: false
  timeout: 300
  
execution:
  safe_mode: true
  max_parallel_tools: 3
  allowed_targets:
    - 192.168.0.0/16
    - 10.0.0.0/8
    
logging:
  level: INFO
  file: /var/log/purple-team-gpt/red-agent.log
```

### Blue Agent (/etc/purple-team-gpt/blue-agent.yaml)

```yaml
agent:
  type: blue
  id: blue-agent-1
  
orchestrator:
  url: http://10.0.0.10:8000
  api_key: ${AGENT_API_KEY}
  
tools:
  auto_install: true
  update_on_start: false
  timeout: 120
  
monitoring:
  log_paths:
    - /var/log/auth.log
    - /var/log/syslog
    - /var/log/nginx/access.log
  check_interval: 5
  
response:
  auto_block: false
  auto_quarantine: false
  firewall: iptables
  
logging:
  level: INFO
  file: /var/log/purple-team-gpt/blue-agent.log
```