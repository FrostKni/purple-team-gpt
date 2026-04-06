#!/bin/bash
# ==============================================================================
# Purple Team GPT - Let's Encrypt SSL Certificate Setup (Production)
# ==============================================================================
# This script sets up Let's Encrypt SSL certificates using certbot for
# production deployments.
#
# Prerequisites:
#   - Domain name pointing to your server
#   - Ports 80 and 443 open and accessible
#   - Docker and docker-compose installed
#
# Usage:
#   ./scripts/setup-letsencrypt.sh --domain yourdomain.com --email admin@yourdomain.com
#
# Options:
#   -d, --domain    Your domain name (required)
#   -e, --email     Email for Let's Encrypt notifications (required)
#   -s, --staging   Use Let's Encrypt staging server (for testing)
#   -r, --renew     Force renewal of certificates
#   -h, --help      Show this help message
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
SSL_DIR="${PROJECT_ROOT}/docker/ssl"
CERTBOT_DIR="${PROJECT_ROOT}/certbot"
DOMAIN=""
EMAIL=""
STAGING=0
RENEW=0

# Help message
usage() {
    echo "Purple Team GPT - Let's Encrypt SSL Setup"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -d, --domain    Your domain name (required)"
    echo "  -e, --email     Email for Let's Encrypt notifications (required)"
    echo "  -s, --staging   Use Let's Encrypt staging server (for testing)"
    echo "  -r, --renew     Force renewal of certificates"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --domain example.com --email admin@example.com"
    echo "  $0 -d example.com -e admin@example.com --staging"
    echo "  $0 --renew -d example.com -e admin@example.com"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -e|--email)
            EMAIL="$2"
            shift 2
            ;;
        -s|--staging)
            STAGING=1
            shift
            ;;
        -r|--renew)
            RENEW=1
            shift
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

# Validate required arguments
if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo -e "${RED}Error: Domain and email are required${NC}"
    usage
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Purple Team GPT - Let's Encrypt Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Domain: ${DOMAIN}"
echo "  Email:  ${EMAIL}"
echo "  Staging: $([ $STAGING -eq 1 ] && echo 'Yes' || echo 'No')"
echo "  Renew:  $([ $RENEW -eq 1 ] && echo 'Yes' || echo 'No')"
echo ""

# Create directories
mkdir -p "${SSL_DIR}"
mkdir -p "${CERTBOT_DIR}/conf"
mkdir -p "${CERTBOT_DIR}/www"
mkdir -p "${CERTBOT_DIR}/logs"

# Set proper permissions
chmod 755 "${CERTBOT_DIR}/www"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Build certbot command arguments
CERTBOT_ARGS="certonly --webroot"
CERTBOT_ARGS="${CERTBOT_ARGS} --webroot-path=/var/www/certbot"
CERTBOT_ARGS="${CERTBOT_ARGS} --email ${EMAIL}"
CERTBOT_ARGS="${CERTBOT_ARGS} --agree-tos"
CERTBOT_ARGS="${CERTBOT_ARGS} --no-eff-email"
CERTBOT_ARGS="${CERTBOT_ARGS} --non-interactive"
CERTBOT_ARGS="${CERTBOT_ARGS} --domain ${DOMAIN}"

# Add www subdomain if not already present
if [[ ! "$DOMAIN" =~ ^www\. ]]; then
    CERTBOT_ARGS="${CERTBOT_ARGS} --domain www.${DOMAIN}"
fi

# Add staging flag if requested
if [ $STAGING -eq 1 ]; then
    echo -e "${YELLOW}Using Let's Encrypt STAGING server${NC}"
    echo "Certificates will NOT be trusted. Use for testing only."
    CERTBOT_ARGS="${CERTBOT_ARGS} --staging"
fi

# Add force-renewal if requested
if [ $RENEW -eq 1 ]; then
    echo -e "${YELLOW}Force renewal requested${NC}"
    CERTBOT_ARGS="${CERTBOT_ARGS} --force-renewal"
fi

echo -e "${YELLOW}Requesting certificate from Let's Encrypt...${NC}"
echo ""

# Run certbot
docker run --rm \
    -v "${CERTBOT_DIR}/conf:/etc/letsencrypt" \
    -v "${CERTBOT_DIR}/www:/var/www/certbot" \
    -v "${CERTBOT_DIR}/logs:/var/log/letsencrypt" \
    certbot/certbot:latest \
    $CERTBOT_ARGS

# Check if certificate was obtained
CERT_PATH="${CERTBOT_DIR}/conf/live/${DOMAIN}"
if [ -d "$CERT_PATH" ]; then
    echo ""
    echo -e "${GREEN}Certificate obtained successfully!${NC}"
    
    # Create symbolic links to the SSL directory
    ln -sf "${CERT_PATH}/fullchain.pem" "${SSL_DIR}/fullchain.pem"
    ln -sf "${CERT_PATH}/privkey.pem" "${SSL_DIR}/privkey.pem"
    
    echo -e "${GREEN}Symlinks created in ${SSL_DIR}${NC}"
    
    # Display certificate info
    echo ""
    echo -e "${BLUE}Certificate Information:${NC}"
    openssl x509 -in "${CERT_PATH}/fullchain.pem" -noout -dates -subject
    
    # Set up auto-renewal
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Setting up Auto-Renewal${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Let's Encrypt certificates are valid for 90 days."
    echo "Auto-renewal is handled by the certbot service in docker-compose."
    echo ""
    echo -e "${YELLOW}To manually test renewal:${NC}"
    echo "  docker-compose run --rm certbot renew --dry-run"
    echo ""
    echo -e "${YELLOW}To manually renew certificates:${NC}"
    echo "  docker-compose run --rm certbot renew"
    echo ""
else
    echo -e "${RED}Failed to obtain certificate${NC}"
    exit 1
fi

# Update .env file with domain
if [ -f "${PROJECT_ROOT}/.env" ]; then
    if grep -q "^DOMAIN=" "${PROJECT_ROOT}/.env"; then
        sed -i "s|^DOMAIN=.*|DOMAIN=${DOMAIN}|" "${PROJECT_ROOT}/.env"
    else
        echo "DOMAIN=${DOMAIN}" >> "${PROJECT_ROOT}/.env"
    fi
    echo -e "${GREEN}Updated DOMAIN in .env${NC}"
fi

# Final instructions
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Next Steps${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. Update your nginx configuration with the correct domain:"
echo "   server_name ${DOMAIN} www.${DOMAIN};"
echo ""
echo "2. Restart nginx to load the new certificates:"
echo "   docker-compose restart nginx"
echo ""
echo "3. Verify SSL is working:"
echo "   curl -I https://${DOMAIN}"
echo ""
echo "4. Test your SSL configuration:"
echo "   https://www.ssllabs.com/ssltest/analyze.html?d=${DOMAIN}"
echo ""

echo -e "${GREEN}Let's Encrypt setup complete!${NC}"