#!/bin/bash
# Purple Team GPT - Restore Script
# Restores data from backup

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}Usage: ./restore.sh <backup-file.tar.gz>${NC}"
    echo ""
    echo "Available backups:"
    ls -lh backups/*.tar.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Purple Team GPT - Restore${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Restoring from: $BACKUP_FILE"
echo ""

# Stop services
echo -e "${YELLOW}Stopping services...${NC}"
docker-compose down

# Extract backup
echo -e "${YELLOW}Extracting backup...${NC}"
TEMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_DIR=$(ls "$TEMP_DIR")

# Restore ChromaDB
echo -e "${YELLOW}Restoring ChromaDB...${NC}"
if [ -f "$TEMP_DIR/$BACKUP_DIR/chromadb.tar.gz" ]; then
    # Start ChromaDB first
    docker-compose up -d chromadb
    sleep 5
    # Restore data
    docker exec -i purple-team-chromadb tar -xzf - -C / < "$TEMP_DIR/$BACKUP_DIR/chromadb.tar.gz"
    echo -e "${GREEN}ChromaDB restored${NC}"
fi

# Restore Redis
echo -e "${YELLOW}Restoring Redis...${NC}"
if [ -f "$TEMP_DIR/$BACKUP_DIR/redis.rdb" ]; then
    docker-compose up -d redis
    sleep 3
    docker cp "$TEMP_DIR/$BACKUP_DIR/redis.rdb" purple-team-redis:/data/dump.rdb
    docker-compose restart redis
    echo -e "${GREEN}Redis restored${NC}"
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Restore completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Start services with: ${BLUE}./start.sh${NC} or ${BLUE}./dev.sh${NC}"