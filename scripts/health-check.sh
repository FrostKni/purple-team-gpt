#!/bin/bash
# Purple Team GPT - Health Check Script
# Comprehensive health monitoring for all services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
CHROMADB_URL="${CHROMADB_URL:-http://localhost:8001}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Counters
HEALTHY=0
UNHEALTHY=0

check_service() {
    local name=$1
    local check_command=$2
    
    echo -n "Checking $name... "
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}HEALTHY${NC}"
        ((HEALTHY++))
        return 0
    else
        echo -e "${RED}UNHEALTHY${NC}"
        ((UNHEALTHY++))
        return 1
    fi
}

check_http() {
    local name=$1
    local url=$2
    
    echo -n "Checking $name ($url)... "
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}HEALTHY${NC}"
        ((HEALTHY++))
        return 0
    else
        echo -e "${RED}UNHEALTHY${NC}"
        ((UNHEALTHY++))
        return 1
    fi
}

echo "=========================================="
echo "Purple Team GPT - Health Check"
echo "=========================================="
echo ""

# Check Backend
check_http "Backend API" "$BACKEND_URL/health"
check_http "Backend Detailed" "$BACKEND_URL/status"

# Check ChromaDB
check_http "ChromaDB" "$CHROMADB_URL/api/v1/heartbeat"

# Check Redis
echo -n "Checking Redis ($REDIS_HOST:$REDIS_PORT)... "
if docker exec purple-team-redis redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}HEALTHY${NC}"
    ((HEALTHY++))
else
    echo -e "${RED}UNHEALTHY${NC}"
    ((UNHEALTHY++))
fi

# Check Frontend
check_http "Frontend" "$FRONTEND_URL/health"

# Check Docker containers
echo ""
echo "Docker Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=purple-team"

# Summary
echo ""
echo "=========================================="
echo "Summary: $HEALTHY healthy, $UNHEALTHY unhealthy"
echo "=========================================="

if [ $UNHEALTHY -gt 0 ]; then
    echo -e "${YELLOW}Some services are unhealthy. Check logs with:${NC}"
    echo "  docker-compose logs -f"
    exit 1
fi

echo -e "${GREEN}All services are healthy!${NC}"
exit 0