#!/bin/bash
# Purple Team GPT - Backup Script
# Creates backups of all persistent data

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_PATH"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Purple Team GPT - Backup${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Backup location: $BACKUP_PATH"
echo ""

# Backup ChromaDB
echo -e "${YELLOW}Backing up ChromaDB...${NC}"
if docker ps | grep -q purple-team-chromadb; then
    docker exec purple-team-chromadb tar -czf - /chroma/chroma > "$BACKUP_PATH/chromadb.tar.gz"
    echo -e "${GREEN}ChromaDB backed up: chromadb.tar.gz${NC}"
else
    echo -e "${RED}ChromaDB container not running${NC}"
fi

# Backup Redis
echo -e "${YELLOW}Backing up Redis...${NC}"
if docker ps | grep -q purple-team-redis; then
    docker exec purple-team-redis redis-cli BGSAVE
    sleep 2
    docker cp purple-team-redis:/data/dump.rdb "$BACKUP_PATH/redis.rdb"
    echo -e "${GREEN}Redis backed up: redis.rdb${NC}"
else
    echo -e "${RED}Redis container not running${NC}"
fi

# Backup Feedback Database
echo -e "${YELLOW}Backing up Feedback Database...${NC}"
if docker ps | grep -q purple-team-backend; then
    docker exec purple-team-backend find /app/data -name "*.db" -exec tar -czf - {} \; > "$BACKUP_PATH/feedback_db.tar.gz" 2>/dev/null || true
    echo -e "${GREEN}Feedback database backed up${NC}"
fi

# Backup configuration
echo -e "${YELLOW}Backing up configuration...${NC}"
if [ -f .env ]; then
    cp .env "$BACKUP_PATH/.env.backup"
    echo -e "${GREEN}Environment file backed up${NC}"
fi

# Create backup manifest
echo -e "${YELLOW}Creating backup manifest...${NC}"
cat > "$BACKUP_PATH/manifest.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date -Iseconds)",
    "version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')",
    "files": [
        $(ls -1 "$BACKUP_PATH" | grep -v manifest.json | sed 's/\(.*\)/"\1"/' | tr '\n' ',' | sed 's/,$//')
    ]
}
EOF

# Compress entire backup
echo -e "${YELLOW}Compressing backup...${NC}"
tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR" "$TIMESTAMP"
rm -rf "$BACKUP_PATH"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backup completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Backup file: $BACKUP_PATH.tar.gz"
echo -e "Size: $(du -h "$BACKUP_PATH.tar.gz" | cut -f1)"

# Cleanup old backups (keep last 7)
echo ""
echo -e "${YELLOW}Cleaning up old backups...${NC}"
ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm
echo -e "${GREEN}Done${NC}"