#!/bin/bash
# =============================================================================
# Purple Team GPT - Red Agent Entrypoint
# =============================================================================
# Initialize and run the Red Agent service

set -e

echo "=========================================="
echo "🔴 Purple Team GPT - Red Agent (Kali)"
echo "=========================================="

# Display system information
echo "System: $(uname -a)"
echo "Python: $(python3 --version)"
echo "Agent Type: ${AGENT_TYPE:-red}"

# Initialize tool directories
mkdir -p /opt/loot /opt/payloads /opt/reports

# Update Nuclei templates if nuclei is available
if command -v nuclei &> /dev/null; then
    echo "Updating Nuclei templates..."
    nuclei -update-templates 2>/dev/null || true
fi

# Check for wordlists
if [ -f /usr/share/wordlists/rockyou.txt ]; then
    echo "✓ Rockyou wordlist available"
fi

# List available tools
echo ""
echo "=== Available Offensive Tools ==="
echo "Scanning: nmap, masscan, rustscan"
echo "Web: nikto, nuclei, gobuster, ffuf, sqlmap"
echo "Passwords: hydra, john, hashcat"
echo "Exploitation: metasploit, crackmapexec"
echo "AD: bloodhound, impacket, kerbrute"
echo "Wireless: aircrack-ng, wifite"
echo ""

# Start the service
echo "Starting Red Agent service..."
exec "$@"