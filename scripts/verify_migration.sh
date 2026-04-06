#!/bin/bash
# Verify database migration status
# Usage: ./scripts/verify_migration.sh

set -e

echo "=== Purple Team GPT - Migration Verification ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Check if PostgreSQL is running
echo "1. Checking PostgreSQL status..."
if docker ps | grep -q purple-team-postgres; then
    echo -e "${GREEN}✓ PostgreSQL container is running${NC}"
elif systemctl is-active --quiet postgresql; then
    echo -e "${GREEN}✓ PostgreSQL service is running${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL is not running${NC}"
    echo ""
    echo "To start PostgreSQL with Docker:"
    echo "  docker-compose up -d postgres"
    echo ""
    echo "Or with Docker Compose V2:"
    echo "  docker compose up -d postgres"
    exit 1
fi

# Check current migration status
echo ""
echo "2. Checking migration status..."
unset AGENT  # Unset AGENT env var that conflicts with settings
PYTHONPATH=./src:$PYTHONPATH python -m alembic current

# List all tables if connected
echo ""
echo "3. Verifying tables..."
TABLES=$(PYTHONPATH=./src:$PYTHONPATH python << 'PYEOF'
import asyncio
from purple_team_gpt.db.database import get_db
from sqlalchemy import text

async def get_tables():
    async for db in get_db():
        result = await db.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        ))
        tables = [row[0] for row in result]
        return tables

tables = asyncio.run(get_tables())
for table in tables:
    print(table)
PYEOF
)

if [ -n "$TABLES" ]; then
    echo -e "${GREEN}✓ Tables found:${NC}"
    echo "$TABLES"
else
    echo -e "${YELLOW}⚠ No tables found - migration may need to be applied${NC}"
    echo ""
    echo "To apply migration:"
    echo "  unset AGENT && PYTHONPATH=./src:\$PYTHONPATH python -m alembic upgrade head"
fi

echo ""
echo "=== Verification Complete ==="
