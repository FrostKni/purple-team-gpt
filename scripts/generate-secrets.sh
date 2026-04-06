#!/bin/bash
# ==============================================================================
# Purple Team GPT - Secure Secrets Generator
# ==============================================================================
# This script generates cryptographically secure secrets for production use.
#
# Usage:
#   ./scripts/generate-secrets.sh [options]
#
# Options:
#   -o, --output     Output file (default: .env.production)
#   -f, --format     Output format: env, json, docker (default: env)
#   -l, --length    Secret length in bytes (default: 32)
#   -h, --help      Show this help message
#
# Generated secrets:
#   - APP_SECRET_KEY      (JWT signing)
#   - DB_PASSWORD         (PostgreSQL)
#   - REDIS_PASSWORD      (Redis)
#   - CHROMA_AUTH_TOKEN   (ChromaDB)
#   - API_KEY_SALT        (API key generation)
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_FILE=""
FORMAT="env"
SECRET_LENGTH=32

# Help message
usage() {
    echo "Purple Team GPT - Secure Secrets Generator"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -o, --output    Output file (default: stdout)"
    echo "  -f, --format    Output format: env, json, docker (default: env)"
    echo "  -l, --length    Secret length in bytes (default: 32)"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Print secrets to stdout"
    echo "  $0 -o .env.production        # Write to .env.production"
    echo "  $0 -f json                   # Output as JSON"
    echo "  $0 -f docker -o secrets.yml  # Docker Compose secrets format"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -l|--length)
            SECRET_LENGTH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate format
if [[ ! "$FORMAT" =~ ^(env|json|docker)$ ]]; then
    echo -e "${RED}Error: Invalid format '${FORMAT}'. Use: env, json, or docker${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Purple Team GPT - Secrets Generator${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for openssl or Python
generate_secret() {
    local length=$1
    if command -v openssl &> /dev/null; then
        openssl rand -hex "$length"
    elif command -v python3 &> /dev/null; then
        python3 -c "import secrets; print(secrets.token_hex($length))"
    elif command -v python &> /dev/null; then
        python -c "import secrets; print(secrets.token_hex($length))"
    else
        echo -e "${RED}Error: Neither openssl nor Python is available${NC}" >&2
        exit 1
    fi
}

# Generate all secrets
echo -e "${YELLOW}Generating cryptographically secure secrets...${NC}"
echo ""

APP_SECRET_KEY=$(generate_secret $SECRET_LENGTH)
DB_PASSWORD=$(generate_secret $SECRET_LENGTH)
REDIS_PASSWORD=$(generate_secret $SECRET_LENGTH)
CHROMA_AUTH_TOKEN=$(generate_secret $SECRET_LENGTH)
API_KEY_SALT=$(generate_secret 16)

# Generate timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Generate output based on format
generate_output() {
    case $FORMAT in
        env)
            cat << EOF
# ==============================================================================
# Purple Team GPT - Production Secrets
# Generated: ${TIMESTAMP}
# ==============================================================================
# WARNING: Keep this file secure and never commit to version control!
# Add to .gitignore: .env.production, .env.*.local
# ==============================================================================

# Application Secret Key (JWT signing)
# Minimum 32 characters recommended
APP_SECRET_KEY=${APP_SECRET_KEY}

# Database Password (PostgreSQL)
DB_PASSWORD=${DB_PASSWORD}

# Redis Password
REDIS_PASSWORD=${REDIS_PASSWORD}

# ChromaDB Authentication Token
CHROMA_AUTH_TOKEN=${CHROMA_AUTH_TOKEN}

# API Key Salt (for generating API keys)
API_KEY_SALT=${API_KEY_SALT}

# ==============================================================================
# Additional Security Recommendations
# ==============================================================================
# 1. Rotate these secrets every 90 days
# 2. Use a secrets manager (HashiCorp Vault, AWS Secrets Manager, etc.)
# 3. Set file permissions: chmod 600 .env.production
# 4. Use different secrets for each environment
# 5. Never share secrets via email, chat, or unencrypted channels
# ==============================================================================
EOF
            ;;
        json)
            cat << EOF
{
  "generated_at": "${TIMESTAMP}",
  "secrets": {
    "app_secret_key": "${APP_SECRET_KEY}",
    "db_password": "${DB_PASSWORD}",
    "redis_password": "${REDIS_PASSWORD}",
    "chroma_auth_token": "${CHROMA_AUTH_TOKEN}",
    "api_key_salt": "${API_KEY_SALT}"
  },
  "_security": {
    "warning": "Keep this file secure and never commit to version control",
    "rotation_policy": "Rotate every 90 days",
    "environments": "Use different secrets for each environment"
  }
}
EOF
            ;;
        docker)
            cat << EOF
# Docker Compose Secrets Configuration
# Generated: ${TIMESTAMP}
# Add this to your docker-compose.yml or use as external secrets file

secrets:
  app_secret_key:
    file: ./secrets/app_secret_key.txt
  db_password:
    file: ./secrets/db_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
  chroma_auth_token:
    file: ./secrets/chroma_auth_token.txt

# To create secret files:
# mkdir -p secrets
# echo "${APP_SECRET_KEY}" > secrets/app_secret_key.txt
# echo "${DB_PASSWORD}" > secrets/db_password.txt
# echo "${REDIS_PASSWORD}" > secrets/redis_password.txt
# echo "${CHROMA_AUTH_TOKEN}" > secrets/chroma_auth_token.txt
# chmod 600 secrets/*.txt
EOF
            ;;
    esac
}

# Output to file or stdout
if [ -n "$OUTPUT_FILE" ]; then
    generate_output > "$OUTPUT_FILE"
    chmod 600 "$OUTPUT_FILE"
    echo -e "${GREEN}Secrets written to: ${OUTPUT_FILE}${NC}"
    echo -e "${YELLOW}File permissions set to 600 (owner read/write only)${NC}"
else
    generate_output
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Security Checklist${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "[ ] Store secrets in a password manager or secrets vault"
echo -e "[ ] Configure backup and recovery procedures"
echo -e "[ ] Set up secret rotation schedule (90 days max)"
echo -e "[ ] Ensure secrets are different per environment"
echo -e "[ ] Verify .gitignore includes secret files"
echo -e "[ ] Document secret access and audit procedures"
echo ""

if [ -n "$OUTPUT_FILE" ]; then
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Review the generated secrets in: ${OUTPUT_FILE}"
    echo "2. Copy to your production environment securely"
    echo "3. Delete local copies after deployment"
    echo ""
fi

echo -e "${GREEN}Secret generation complete!${NC}"