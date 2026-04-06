#!/bin/bash
# Purple Team GPT - Stop Script
# Graceful shutdown of all services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Purple Team GPT - Stopping Services${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if running
if ! docker-compose ps 2>/dev/null | grep -q "Up"; then
    echo -e "${YELLOW}No services are currently running${NC}"
    exit 0
fi

# Graceful shutdown
echo -e "${YELLOW}Initiating graceful shutdown...${NC}"
docker-compose down --timeout 30

# Check for cleanup
if [ "$1" == "--clean" ]; then
    echo -e "${YELLOW}Removing volumes...${NC}"
    docker-compose down -v
    echo -e "${GREEN}Volumes removed${NC}"
fi

echo -e "${GREEN}Services stopped successfully${NC}"