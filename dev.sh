#!/bin/bash
# Purple Team GPT - Development Startup Script
# Usage: ./dev.sh [options]
#
# Options:
#   --build     Force rebuild of Docker images
#   --clean     Clean up volumes and rebuild from scratch
#   --logs      Show logs after startup
#   --help      Show this help message

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
BUILD=false
CLEAN=false
SHOW_LOGS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --help)
            echo "Purple Team GPT - Development Environment"
            echo ""
            echo "Usage: ./dev.sh [options]"
            echo ""
            echo "Options:"
            echo "  --build     Force rebuild of Docker images"
            echo "  --clean     Clean up volumes and rebuild from scratch"
            echo "  --logs      Show logs after startup"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Purple Team GPT - Development Environment${NC}"
echo -e "${BLUE}========================================${NC}"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Created .env file. Please configure your API keys.${NC}"
    echo -e "${YELLOW}Edit .env and restart: ./dev.sh${NC}"
    exit 0
fi

# Check for required tools
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed.${NC}"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Docker Compose is required but not installed.${NC}"; exit 1; }

# Clean option
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}Cleaning up existing containers and volumes...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v --remove-orphans
    docker system prune -f
    BUILD=true
fi

# Check if containers are already running
if docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}Containers are already running.${NC}"
    echo -e "Use ${BLUE}docker-compose logs -f${NC} to view logs"
    echo -e "Use ${BLUE}docker-compose down${NC} to stop"
    exit 0
fi

# Build images
if [ "$BUILD" = true ]; then
    echo -e "${BLUE}Building Docker images...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
fi

# Start services
echo -e "${BLUE}Starting services...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Wait for services to be healthy
echo -e "${BLUE}Waiting for services to be ready...${NC}"

# Wait for backend
echo -e "Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is healthy!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Backend failed to start${NC}"
        docker-compose logs backend
        exit 1
    fi
    sleep 2
done

# Wait for ChromaDB
echo -e "Waiting for ChromaDB..."
for i in {1..30}; do
    if curl -s http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; then
        echo -e "${GREEN}ChromaDB is healthy!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}ChromaDB failed to start${NC}"
        docker-compose logs chromadb
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
        docker-compose logs redis
        exit 1
    fi
    sleep 1
done

# Wait for Frontend
echo -e "Waiting for Frontend..."
sleep 5
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}Frontend is healthy!${NC}"
else
    echo -e "${YELLOW}Frontend may still be starting...${NC}"
fi

# Print status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Development environment is ready!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Services:"
echo -e "  ${BLUE}Backend:${NC}    http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}   http://localhost:8000/docs"
echo -e "  ${BLUE}Frontend:${NC}   http://localhost:5173"
echo -e "  ${BLUE}ChromaDB:${NC}   http://localhost:8001"
echo -e "  ${BLUE}Redis:${NC}      localhost:6379"
echo ""
echo -e "Commands:"
echo -e "  ${BLUE}docker-compose logs -f${NC}     View logs"
echo -e "  ${BLUE}docker-compose down${NC}        Stop services"
echo -e "  ${BLUE}docker-compose restart${NC}     Restart services"
echo ""

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
    docker-compose logs -f
fi