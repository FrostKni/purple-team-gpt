#!/bin/bash
# =============================================================================
# Purple Team GPT - Docker Experimentation Quick Start
# =============================================================================
# This script sets up and runs the complete Purple Team GPT environment
# in Docker containers for experimentation purposes.
#
# Usage:
#   ./docker-start.sh [command]
#
# Commands:
#   build     - Build all Docker images
#   up        - Start all services
#   down      - Stop all services
#   logs      - View logs
#   status    - Check service status
#   shell     - Open shell in a container
#   test      - Run tests
#   clean     - Remove all containers and volumes
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.experiment.yml"
PROJECT_NAME="purple-team-gpt"

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "============================================"
    echo "  Purple Team GPT - Docker Environment"
    echo "============================================"
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed.${NC}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed.${NC}"
        exit 1
    fi
    
    # Check .env file
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
        cp .env.example .env
        echo -e "${GREEN}Created .env file. Please edit it with your API keys.${NC}"
    fi
    
    echo -e "${GREEN}✓ Prerequisites OK${NC}"
}

# Build all images
build() {
    echo -e "${BLUE}Building Docker images...${NC}"
    
    # Build orchestrator
    echo -e "${YELLOW}Building Orchestrator...${NC}"
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME build orchestrator
    
    # Build Red Agent (Kali)
    echo -e "${YELLOW}Building Red Agent (Kali Linux)...${NC}"
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME build red-agent
    
    # Build Blue Agent (Ubuntu)
    echo -e "${YELLOW}Building Blue Agent (Ubuntu Server)...${NC}"
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME build blue-agent
    
    echo -e "${GREEN}✓ All images built successfully!${NC}"
    
    # Show image sizes
    echo -e "\n${BLUE}Image sizes:${NC}"
    docker images | grep purple-team
}

# Start all services
up() {
    echo -e "${BLUE}Starting services...${NC}"
    
    # Start core services first
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d chromadb redis
    
    echo -e "${YELLOW}Waiting for databases to be ready...${NC}"
    sleep 10
    
    # Start main services
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d orchestrator
    
    echo -e "${YELLOW}Waiting for orchestrator...${NC}"
    sleep 15
    
    # Start agents
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d red-agent blue-agent
    
    echo -e "${GREEN}✓ All services started!${NC}"
    status
}

# Stop all services
down() {
    echo -e "${BLUE}Stopping services...${NC}"
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down
    echo -e "${GREEN}✓ Services stopped${NC}"
}

# View logs
logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f
    else
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f $service
    fi
}

# Check status
status() {
    echo -e "${BLUE}Service Status:${NC}"
    echo ""
    docker compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
    echo ""
    
    # Check health
    echo -e "${BLUE}Health Checks:${NC}"
    for service in orchestrator red-agent blue-agent chromadb redis; do
        container="${PROJECT_NAME}-${service}-1"
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
        case $health in
            healthy) echo -e "  $service: ${GREEN}$health${NC}" ;;
            unhealthy) echo -e "  $service: ${RED}$health${NC}" ;;
            *) echo -e "  $service: ${YELLOW}$health${NC}" ;;
        esac
    done
}

# Open shell
shell() {
    local service=$1
    if [ -z "$service" ]; then
        echo -e "${YELLOW}Usage: $0 shell <service>${NC}"
        echo "Available services: orchestrator, red-agent, blue-agent"
        exit 1
    fi
    
    case $service in
        red-agent)
            docker exec -it purple-team-red-agent /bin/bash
            ;;
        blue-agent)
            docker exec -it purple-team-blue-agent /bin/bash
            ;;
        orchestrator)
            docker exec -it purple-team-orchestrator /bin/bash
            ;;
        *)
            echo -e "${RED}Unknown service: $service${NC}"
            exit 1
            ;;
    esac
}

# Run tests
test() {
    echo -e "${BLUE}Running tests...${NC}"
    docker exec -it purple-team-orchestrator python -m pytest tests/ -v
}

# Clean up
clean() {
    echo -e "${RED}⚠ This will remove all containers, volumes, and images!${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v --rmi local
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    fi
}

# Show available tools in Red Agent
show_red_tools() {
    echo -e "${BLUE}=== Red Agent Tools (Kali Linux) ===${NC}"
    docker exec purple-team-red-agent bash -c '
        echo "Scanning: $(which nmap 2>/dev/null && echo "✓ nmap" || echo "✗ nmap")"
        echo "Web: $(which nikto 2>/dev/null && echo "✓ nikto" || echo "✗ nikto")"
        echo "SQL: $(which sqlmap 2>/dev/null && echo "✓ sqlmap" || echo "✗ sqlmap")"
        echo "Brute: $(which hydra 2>/dev/null && echo "✓ hydra" || echo "✗ hydra")"
        echo "Exploit: $(which msfconsole 2>/dev/null && echo "✓ metasploit" || echo "✗ metasploit")"
        echo "AD: $(which crackmapexec 2>/dev/null && echo "✓ crackmapexec" || echo "✗ crackmapexec")"
        echo "Wireless: $(which aircrack-ng 2>/dev/null && echo "✓ aircrack" || echo "✗ aircrack")"
    '
}

# Show available tools in Blue Agent
show_blue_tools() {
    echo -e "${BLUE}=== Blue Agent Tools (Ubuntu Server) ===${NC}"
    docker exec purple-team-blue-agent bash -c '
        echo "Firewall: $(which iptables 2>/dev/null && echo "✓ iptables" || echo "✗ iptables")"
        echo "IDS: $(which suricata 2>/dev/null && echo "✓ suricata" || echo "✗ suricata")"
        echo "HIDS: $(which aide 2>/dev/null && echo "✓ aide" || echo "✗ aide")"
        echo "Malware: $(which clamscan 2>/dev/null && echo "✓ clamav" || echo "✗ clamav")"
        echo "Audit: $(which auditd 2>/dev/null && echo "✓ auditd" || echo "✗ auditd")"
        echo "Forensics: $(which volatility 2>/dev/null && echo "✓ volatility" || echo "✗ volatility")"
        echo "Monitor: $(which tcpdump 2>/dev/null && echo "✓ tcpdump" || echo "✗ tcpdump")"
    '
}

# Main command dispatcher
case "$1" in
    build)
        check_prerequisites
        build
        ;;
    up)
        check_prerequisites
        up
        ;;
    down)
        down
        ;;
    logs)
        logs "$2"
        ;;
    status)
        status
        ;;
    shell)
        shell "$2"
        ;;
    test)
        test
        ;;
    clean)
        clean
        ;;
    tools)
        show_red_tools
        echo ""
        show_blue_tools
        ;;
    *)
        print_banner
        echo "Usage: $0 {build|up|down|logs|status|shell|test|clean|tools}"
        echo ""
        echo "Commands:"
        echo "  build   - Build all Docker images"
        echo "  up      - Start all services"
        echo "  down    - Stop all services"
        echo "  logs    - View logs (optional: service name)"
        echo "  status  - Check service status"
        echo "  shell   - Open shell in container (orchestrator|red-agent|blue-agent)"
        echo "  test    - Run tests"
        echo "  clean   - Remove all containers and volumes"
        echo "  tools   - Show available tools in agents"
        echo ""
        echo "Quick Start:"
        echo "  1. Edit .env file with your API keys"
        echo "  2. ./docker-start.sh build"
        echo "  3. ./docker-start.sh up"
        echo "  4. Access: http://localhost:8000"
        ;;
esac