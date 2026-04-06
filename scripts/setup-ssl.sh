#!/bin/bash
# ==============================================================================
# Purple Team GPT - Self-Signed SSL Certificate Setup (Development Only)
# ==============================================================================
# This script generates self-signed SSL certificates for local development.
# DO NOT use in production - use Let's Encrypt or a proper CA instead.
#
# Usage:
#   ./scripts/setup-ssl.sh [domain]
#
# Arguments:
#   domain - Optional domain name (default: localhost)
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSL_DIR="${PROJECT_ROOT}/docker/ssl"
DOMAIN="${1:-localhost}"
CERT_FILE="${SSL_DIR}/fullchain.pem"
KEY_FILE="${SSL_DIR}/privkey.pem"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Purple Team GPT - SSL Setup (Dev)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if openssl is installed
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: openssl is not installed${NC}"
    echo "Please install openssl first:"
    echo "  Ubuntu/Debian: sudo apt-get install openssl"
    echo "  macOS: brew install openssl"
    exit 1
fi

# Create SSL directory
mkdir -p "${SSL_DIR}"

echo -e "${YELLOW}Generating self-signed certificate for: ${DOMAIN}${NC}"
echo ""

# Generate DH parameters (for perfect forward secrecy)
if [ ! -f "${SSL_DIR}/dhparam.pem" ]; then
    echo -e "${YELLOW}Generating DH parameters (this may take a minute)...${NC}"
    openssl dhparam -out "${SSL_DIR}/dhparam.pem" 2048 2>/dev/null
    echo -e "${GREEN}DH parameters generated${NC}"
else
    echo -e "${GREEN}DH parameters already exist${NC}"
fi

# Generate private key and certificate
echo -e "${YELLOW}Generating private key and self-signed certificate...${NC}"

# Create a temporary config file for SAN (Subject Alternative Names)
cat > "${SSL_DIR}/openssl.cnf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
C = US
ST = California
L = San Francisco
O = Purple Team GPT
OU = Development
CN = ${DOMAIN}

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = localhost
DNS.3 = *.localhost
DNS.4 = 127.0.0.1
IP.1 = 127.0.0.1
EOF

# Generate the certificate
openssl req -new -x509 -days 365 -nodes \
    -keyout "${KEY_FILE}" \
    -out "${CERT_FILE}" \
    -config "${SSL_DIR}/openssl.cnf" \
    2>/dev/null

# Set proper permissions
chmod 644 "${CERT_FILE}"
chmod 600 "${KEY_FILE}"

echo -e "${GREEN}SSL certificates generated successfully!${NC}"
echo ""
echo -e "${BLUE}Certificate files:${NC}"
echo "  Certificate: ${CERT_FILE}"
echo "  Private Key: ${KEY_FILE}"
echo "  DH Params:   ${SSL_DIR}/dhparam.pem"
echo ""

# Display certificate info
echo -e "${BLUE}Certificate Information:${NC}"
openssl x509 -in "${CERT_FILE}" -noout -text | grep -A2 "Subject:"
echo ""

# Trust instructions
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}IMPORTANT: Trust the Certificate${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "Your browser will show a security warning because this is a self-signed"
echo "certificate. For development, you can:"
echo ""
echo -e "${GREEN}Option 1: Accept the warning in your browser${NC}"
echo "  Navigate to https://localhost:3000 and accept the security warning."
echo ""
echo -e "${GREEN}Option 2: Trust the certificate system-wide${NC}"
echo ""
echo "  Linux (Debian/Ubuntu):"
echo "    sudo cp ${CERT_FILE} /usr/local/share/ca-certificates/purple-team-gpt.crt"
echo "    sudo update-ca-certificates"
echo ""
echo "  macOS:"
echo "    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ${CERT_FILE}"
echo ""
echo "  Windows (PowerShell as Admin):"
echo "    Import-Certificate -FilePath '${CERT_FILE}' -CertStoreLocation Cert:\LocalMachine\Root"
echo ""

# Update nginx config to use the DH params
echo -e "${BLUE}Note: To enable DH parameters in nginx, uncomment this line in nginx.conf:${NC}"
echo "  ssl_dhparam /etc/nginx/dhparam.pem;"
echo ""

echo -e "${GREEN}SSL setup complete!${NC}"