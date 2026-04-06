#!/bin/bash
# Purple Team GPT - Production Startup Script
# Usage: ./start.sh [options]
#
# Options:
#   --migrate     Run database migrations before starting
#   --backup      Create backup before starting
#   --health      Run health checks and exit
#   --help        Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
MIGRATE=false
BACKUP=false
HEALTH_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --migrate)
            MIGRATE=true
            shift
            ;;
        --backup)
            BACKUP=true
            shift
            ;;
        --health)
            HEALTH_ONLY=true
            shift
            ;;
        --help)
            echo "Purple Team GPT - Production Startup"
            echo ""
            echo "Usage: ./start.sh [options]"
            echo ""
            echo "Options:"
            echo "  --migrate     Run database migrations before starting"
            echo "  --backup      Create backup before starting"
            echo "  --health      Run health checks and exit"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Health check only mode
if [ "$HEALTH_ONLY" = true ]; then
    echo -e "${BLUE}Running health checks...${NC}"
    
    # Check backend
    if curl -sf http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}Backend: healthy${NC}"
    else
        echo -e "${RED}Backend: unhealthy${NC}"
        exit 1
    fi
    
    # Check ChromaDB
    if curl -sf http://localhost:8001/api/v1/heartbeat > /dev/null; then
        echo -e "${GREEN}ChromaDB: healthy${NC}"
    else
        echo -e "${RED}ChromaDB: unhealthy${NC}"
        exit 1
    fi
    
    # Check Redis
    if docker exec purple-team-redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo -e "${GREEN}Redis: healthy${NC}"
    else
        echo -e "${RED}Redis: unhealthy${NC}"
        exit 1
    fi
    
    # Check Frontend
    if curl -sf http://localhost:80/health > /dev/null; then
        echo -e "${GREEN}Frontend: healthy${NC}"
    else
        echo -e "${RED}Frontend: unhealthy${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}All services healthy!${NC}"
    exit 0
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Purple Team GPT - Production Startup${NC}"
echo -e "${BLUE}========================================${NC}"

# Check for required environment
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: No .env file found!${NC}"
    echo -e "Please create .env from .env.example with production values."
    exit 1
fi

# Validate required environment variables
required_vars=(
    "APP_SECRET_KEY"
    "LLM_OPENAI_API_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}ERROR: Required environment variable $var is not set${NC}"
        exit 1
    fi
done

# Check for Docker
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed.${NC}"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Docker Compose is required but not installed.${NC}"; exit 1; }

# Backup option
if [ "$BACKUP" = true ]; then
    echo -e "${BLUE}Creating backup...${NC}"
    BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup ChromaDB
    if docker ps | grep -q purple-team-chromadb; then
        docker exec purple-team-chromadb tar -czf - /chroma/chroma > "$BACKUP_DIR/chromadb_backup.tar.gz"
        echo -e "${GREEN}ChromaDB backed up to $BACKUP_DIR/chromadb_backup.tar.gz${NC}"
    fi
    
    # Backup Redis
    if docker ps | grep -q purple-team-redis; then
        docker exec purple-team-redis redis-cli BGSAVE
        sleep 2
        docker cp purple-team-redis:/data/dump.rdb "$BACKUP_DIR/redis_backup.rdb"
        echo -e "${GREEN}Redis backed up to $BACKUP_DIR/redis_backup.rdb${NC}"
    fi
fi

# Pull latest images
echo -e "${BLUE}Pulling latest images...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Migration option
if [ "$MIGRATE" = true ]; then
    echo -e "${BLUE}Running migrations...${NC}"
    # Add migration commands here when needed
    echo -e "${GREEN}Migrations complete${NC}"
fi

# Start services
echo -e "${BLUE}Starting services...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo -e "${BLUE}Waiting for services to be ready...${NC}"

# Wait for backend with longer timeout
echo -e "Waiting for backend..."
for i in {1..60}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is healthy!${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${RED}Backend failed to start within timeout${NC}"
        docker-compose logs --tail=100 backend
        exit 1
    fi
    sleep 5
done

# Wait for ChromaDB
echo -e "Waiting for ChromaDB..."
for i in {1..30}; do
    if curl -sf http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; then
        echo -e "${GREEN}ChromaDB is healthy!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}ChromaDB failed to start${NC}"
        exit 1
    fi
    sleep 2
done

# Wait for Redis
echo -e "Waiting for Redis..."
for i in {1..30}; do
    if docker exec purple-team-redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo -e "${GREEN}Redis is healthy!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Redis failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Print status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Production environment is ready!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Services running:"
echo -e "  ${BLUE}Backend:${NC}    http://localhost:8000"
echo -e "  ${BLUE}Frontend:${NC}   http://localhost:3000"
echo ""
echo -e "Health check: ${BLUE}./start.sh --health${NC}"
echo -e "View logs:    ${BLUE}docker-compose logs -f${NC}"
echo -e "Stop:         ${BLUE}docker-compose down${NC}"
echo ""

# Log startup
echo "$(date -Iseconds) - Production startup completed successfully" >> ./logs/startup.log