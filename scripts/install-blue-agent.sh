#!/bin/bash
#===============================================================================
# Purple Team GPT - Blue Agent Installation Script
#
# This script installs the Blue Agent on a defender system.
# The agent runs directly on the system with full access to defensive tools.
#
# Usage:
#   ./install-blue-agent.sh --orchestrator <IP:PORT> [--config /path/to/config.yaml]
#
# Requirements:
#   - Ubuntu Server 22.04+ / Security Onion / Rocky Linux
#   - Root/sudo access
#   - Internet connection
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="/opt/purple-team-gpt"
CONFIG_DIR="/etc/purple-team-gpt"
LOG_DIR="/var/log/purple-team-gpt"
SERVICE_USER="purple-team-blue"
SERVICE_GROUP="purple-team-blue"
AGENT_ID="blue-agent-1"

# Parse arguments
ORCHESTRATOR_URL=""
CONFIG_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --orchestrator|-o)
            ORCHESTRATOR_URL="$2"
            shift 2
            ;;
        --config|-c)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --id)
            AGENT_ID="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Purple Team GPT - Blue Agent Installation                 ║"
echo "║                    [DEFENSIVE SECURITY]                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check orchestrator URL
if [[ -z "$ORCHESTRATOR_URL" ]]; then
    echo -e "${RED}Error: Orchestrator URL is required${NC}"
    echo "Usage: $0 --orchestrator <IP:PORT>"
    exit 1
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script must be run as root${NC}"
    exit 1
fi

# Extract orchestrator host
ORCH_HOST=$(echo $ORCHESTRATOR_URL | sed 's|http://||' | sed 's|https://||' | cut -d: -f1)
ORCH_PORT=$(echo $ORCHESTRATOR_URL | sed 's|http://||' | sed 's|https://||' | cut -d: -f2)
[[ -z "$ORCH_PORT" ]] && ORCH_PORT="8000"
ORCHESTRATOR_URL="http://${ORCH_HOST}:${ORCH_PORT}"

#-------------------------------------------------------------------------------
# Step 1: Install system dependencies
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[1/9] Installing system dependencies...${NC}"

apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    sudo

#-------------------------------------------------------------------------------
# Step 2: Create service user
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[2/9] Creating service user...${NC}"

if ! id -u $SERVICE_USER &>/dev/null; then
    useradd -r -s /bin/bash -d $INSTALL_DIR $SERVICE_USER
    # Allow service user to run commands as root for defensive operations
    echo "$SERVICE_USER ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/purple-team-blue
    echo -e "${GREEN}Created user: $SERVICE_USER${NC}"
else
    echo -e "${GREEN}User already exists: $SERVICE_USER${NC}"
fi

#-------------------------------------------------------------------------------
# Step 3: Create directories
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[3/9] Creating directories...${NC}"

mkdir -p $INSTALL_DIR
mkdir -p $CONFIG_DIR
mkdir -p $LOG_DIR

#-------------------------------------------------------------------------------
# Step 4: Install application
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[4/9] Installing application...${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

if [[ -f "$REPO_ROOT/pyproject.toml" ]]; then
    echo "Copying from local repository..."
    cp -r $REPO_ROOT/* $INSTALL_DIR/
else
    echo "Cloning from GitHub..."
    git clone https://github.com/your-org/purple-team-gpt.git $INSTALL_DIR
fi

#-------------------------------------------------------------------------------
# Step 5: Create virtual environment
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[5/9] Setting up Python environment...${NC}"

cd $INSTALL_DIR
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[blue-agent]"

#-------------------------------------------------------------------------------
# Step 6: Install defensive tools
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[6/9] Installing defensive security tools...${NC}"

# Core defensive tools
apt-get install -y \
    iptables \
    ufw \
    fail2ban \
    rkhunter \
    chkrootkit \
    clamav \
    clamav-daemon \
    auditd \
    audispd-plugins \
    aide \
    tcpdump \
    tshark \
    iftop \
    nethogs \
    htop \
    lsof \
    strace \
    logwatch \
    lynis \
    psad \
    2>/dev/null || echo "Some tools may already be installed"

# Start and enable services
systemctl enable auditd 2>/dev/null || true
systemctl start auditd 2>/dev/null || true

# Initialize AIDE database
aide --init 2>/dev/null && mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db 2>/dev/null || true

# Update ClamAV signatures
freshclam 2>/dev/null || true

echo -e "${GREEN}Defensive tools installed!${NC}"

#-------------------------------------------------------------------------------
# Step 7: Create configuration
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[7/9] Creating configuration...${NC}"

# Generate API key for this agent
AGENT_API_KEY=$(openssl rand -hex 16)
SECRET_KEY=$(openssl rand -hex 32)

# Create config file
cat > $CONFIG_DIR/blue-agent.yaml << EOF
# Purple Team GPT Blue Agent Configuration

agent:
  type: blue
  id: $AGENT_ID

orchestrator:
  url: $ORCHESTRATOR_URL
  api_key: $AGENT_API_KEY

tools:
  auto_install: true
  update_on_start: false
  timeout: 120

monitoring:
  log_paths:
    - /var/log/auth.log
    - /var/log/syslog
    - /var/log/kern.log
    - /var/log/nginx/access.log
    - /var/log/apache2/access.log
  check_interval: 5

response:
  auto_block: false
  auto_quarantine: false
  firewall: iptables

logging:
  level: INFO
  file: $LOG_DIR/blue-agent.log
EOF

# Create environment file
cat > $CONFIG_DIR/environment << EOF
# Blue Agent Environment Variables

AGENT_TYPE=blue
AGENT_ID=$AGENT_ID
ORCHESTRATOR_URL=$ORCHESTRATOR_URL
AGENT_API_KEY=$AGENT_API_KEY
SECRET_KEY=$SECRET_KEY

# LLM Configuration (if agent does local LLM calls)
LLM_DEFAULT_PROVIDER=openai
LLM_OPENAI_API_KEY=

# Tool settings
AUTO_INSTALL_TOOLS=true
UPDATE_TOOLS_ON_START=false
TOOL_TIMEOUT=120
SAFE_MODE=true
EOF

ln -sf $CONFIG_DIR/environment $INSTALL_DIR/.env

echo -e "${GREEN}Configuration created at $CONFIG_DIR/blue-agent.yaml${NC}"

#-------------------------------------------------------------------------------
# Step 8: Create systemd service
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[8/9] Creating systemd service...${NC}"

cat > /etc/systemd/system/purple-team-blue-agent.service << EOF
[Unit]
Description=Purple Team GPT Blue Agent (Defensive)
After=network.target auditd.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=$CONFIG_DIR/environment
ExecStart=$INSTALL_DIR/.venv/bin/python -m purple_team_gpt.services.common.system_agent
Restart=on-failure
RestartSec=5

# Allow network and system operations
CapabilityBoundingSet=CAP_NET_RAW CAP_NET_ADMIN CAP_SYS_PTRACE CAP_SYS_ADMIN
AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN CAP_SYS_PTRACE

# Security (relaxed for monitoring)
NoNewPrivileges=false

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=purple-team-blue-agent

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable purple-team-blue-agent

#-------------------------------------------------------------------------------
# Step 9: Set permissions
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[9/9] Setting permissions...${NC}"

chown -R $SERVICE_USER:$SERVICE_GROUP $INSTALL_DIR
chown -R $SERVICE_USER:$SERVICE_GROUP $CONFIG_DIR
chown -R $SERVICE_USER:$SERVICE_GROUP $LOG_DIR

chmod 600 $CONFIG_DIR/environment
chmod 600 $CONFIG_DIR/blue-agent.yaml

# Allow service user to read logs
usermod -aG adm $SERVICE_USER 2>/dev/null || true
usermod -aG systemd-journal $SERVICE_USER 2>/dev/null || true

#-------------------------------------------------------------------------------
# Done!
#-------------------------------------------------------------------------------
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         Blue Agent Installation Complete!                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "Agent ID:            $AGENT_ID"
echo "Orchestrator:        $ORCHESTRATOR_URL"
echo "Config file:         $CONFIG_DIR/blue-agent.yaml"
echo "Environment file:    $CONFIG_DIR/environment"
echo "API Key:             $AGENT_API_KEY"
echo ""
echo -e "${BLUE}IMPORTANT: Save the API Key - you'll need it for orchestrator config!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Add the agent to orchestrator config:"
echo "   - Agent ID: $AGENT_ID"
echo "   - Agent URL: http://THIS_MACHINE_IP:8000"
echo "   - API Key: $AGENT_API_KEY"
echo ""
echo "2. Configure monitored paths in $CONFIG_DIR/blue-agent.yaml"
echo ""
echo "3. Start the agent:"
echo "   systemctl start purple-team-blue-agent"
echo ""
echo "4. Check status:"
echo "   systemctl status purple-team-blue-agent"
echo ""
echo "5. View logs:"
echo "   journalctl -u purple-team-blue-agent -f"
echo ""