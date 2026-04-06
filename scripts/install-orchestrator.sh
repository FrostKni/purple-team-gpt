#!/bin/bash
#===============================================================================
# Purple Team GPT - Orchestrator Installation Script
#
# This script installs the Orchestrator service on a Linux system.
#
# Usage:
#   ./install-orchestrator.sh [--config /path/to/config.yaml]
#
# Requirements:
#   - Ubuntu 22.04+ or similar Linux
#   - Root/sudo access
#   - Internet connection
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/purple-team-gpt"
CONFIG_DIR="/etc/purple-team-gpt"
LOG_DIR="/var/log/purple-team-gpt"
DATA_DIR="/var/lib/purple-team-gpt"
SERVICE_USER="purple-team"
SERVICE_GROUP="purple-team"

# Parse arguments
CONFIG_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
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
echo "║     Purple Team GPT - Orchestrator Installation               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script must be run as root${NC}"
    exit 1
fi

#-------------------------------------------------------------------------------
# Step 1: Install system dependencies
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[1/8] Installing system dependencies...${NC}"

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
    python3-dev

#-------------------------------------------------------------------------------
# Step 2: Create service user
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[2/8] Creating service user...${NC}"

if ! id -u $SERVICE_USER &>/dev/null; then
    useradd -r -s /bin/false -d $INSTALL_DIR $SERVICE_USER
    echo -e "${GREEN}Created user: $SERVICE_USER${NC}"
else
    echo -e "${GREEN}User already exists: $SERVICE_USER${NC}"
fi

#-------------------------------------------------------------------------------
# Step 3: Create directories
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[3/8] Creating directories...${NC}"

mkdir -p $INSTALL_DIR
mkdir -p $CONFIG_DIR
mkdir -p $LOG_DIR
mkdir -p $DATA_DIR/chromadb

#-------------------------------------------------------------------------------
# Step 4: Clone or copy repository
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[4/8] Installing application...${NC}"

# Check if we're inside the repo
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

if [[ -f "$REPO_ROOT/pyproject.toml" ]]; then
    echo "Copying from local repository..."
    cp -r $REPO_ROOT/* $INSTALL_DIR/
else
    echo "Cloning from GitHub..."
    git clone https://github.com/your-org/purple-team-gpt.git $INSTALL_DIR
fi

#-------------------------------------------------------------------------------
# Step 5: Create virtual environment and install dependencies
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[5/8] Setting up Python environment...${NC}"

cd $INSTALL_DIR
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[orchestrator]"

#-------------------------------------------------------------------------------
# Step 6: Create configuration
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[6/8] Creating configuration...${NC}"

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)

# Create config file
cat > $CONFIG_DIR/orchestrator.yaml << EOF
# Purple Team GPT Orchestrator Configuration

server:
  host: 0.0.0.0
  port: 8000

llm:
  provider: openai
  model: gpt-4o
  api_key: \${OPENAI_API_KEY}

agents:
  red:
    - id: red-agent-1
      url: http://RED_AGENT_IP:8000
  blue:
    - id: blue-agent-1
      url: http://BLUE_AGENT_IP:8000

security:
  secret_key: $SECRET_KEY
  safe_mode: true

storage:
  chroma_persist_dir: $DATA_DIR/chromadb
  audit_log: $LOG_DIR/audit.log
EOF

# Create environment file
cat > $CONFIG_DIR/environment << EOF
# Orchestrator Environment Variables
# Fill in your API keys

OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=
GROQ_API_KEY=
SECRET_KEY=$SECRET_KEY
EOF

# Create .env symlink
ln -sf $CONFIG_DIR/environment $INSTALL_DIR/.env

echo -e "${GREEN}Configuration created at $CONFIG_DIR/orchestrator.yaml${NC}"
echo -e "${YELLOW}Please edit the configuration and add your API keys!${NC}"

#-------------------------------------------------------------------------------
# Step 7: Create systemd service
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[7/8] Creating systemd service...${NC}"

cat > /etc/systemd/system/purple-team-orchestrator.service << EOF
[Unit]
Description=Purple Team GPT Orchestrator
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/.venv/bin"
EnvironmentFile=$CONFIG_DIR/environment
ExecStart=$INSTALL_DIR/.venv/bin/python -m purple_team_gpt.services.orchestrator_service.main
Restart=on-failure
RestartSec=5

# Security
NoNewPrivileges=false
# Uncomment for stricter security:
# ProtectSystem=strict
# ProtectHome=true
# ReadWritePaths=$DATA_DIR $LOG_DIR

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=purple-team-orchestrator

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable purple-team-orchestrator

#-------------------------------------------------------------------------------
# Step 8: Set permissions
#-------------------------------------------------------------------------------
echo -e "${YELLOW}[8/8] Setting permissions...${NC}"

chown -R $SERVICE_USER:$SERVICE_GROUP $INSTALL_DIR
chown -R $SERVICE_USER:$SERVICE_GROUP $CONFIG_DIR
chown -R $SERVICE_USER:$SERVICE_GROUP $LOG_DIR
chown -R $SERVICE_USER:$SERVICE_GROUP $DATA_DIR

chmod 600 $CONFIG_DIR/environment
chmod 600 $CONFIG_DIR/orchestrator.yaml

#-------------------------------------------------------------------------------
# Done!
#-------------------------------------------------------------------------------
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "Configuration file: $CONFIG_DIR/orchestrator.yaml"
echo "Environment file:   $CONFIG_DIR/environment"
echo "Log directory:      $LOG_DIR"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit $CONFIG_DIR/environment and add your API keys"
echo "2. Edit $CONFIG_DIR/orchestrator.yaml and configure agent IPs"
echo "3. Start the service: systemctl start purple-team-orchestrator"
echo "4. Check status:      systemctl status purple-team-orchestrator"
echo "5. View logs:         journalctl -u purple-team-orchestrator -f"
echo ""