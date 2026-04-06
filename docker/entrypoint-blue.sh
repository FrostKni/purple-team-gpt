#!/bin/bash
# =============================================================================
# Purple Team GPT - Blue Agent Entrypoint
# =============================================================================
# Initialize and run the Blue Agent service

set -e

echo "=========================================="
echo "🔵 Purple Team GPT - Blue Agent (Ubuntu)"
echo "=========================================="

# Display system information
echo "System: $(uname -a)"
echo "Python: $(python3 --version)"
echo "Agent Type: ${AGENT_TYPE:-blue}"

# Initialize security services
echo ""
echo "=== Initializing Security Services ==="

# Start auditd (requires privileged mode)
if command -v auditd &> /dev/null; then
    echo "Starting auditd..."
    service auditd start 2>/dev/null || true
fi

# Start rsyslog
if command -v rsyslogd &> /dev/null; then
    echo "Starting rsyslog..."
    service rsyslog start 2>/dev/null || true
fi

# Initialize AIDE if database doesn't exist
if [ ! -f /var/lib/aide/aide.db.new ]; then
    echo "Initializing AIDE database..."
    aideinit -y 2>/dev/null || true
fi

# Update ClamAV database
if command -v freshclam &> /dev/null; then
    echo "Updating ClamAV signatures..."
    freshclam 2>/dev/null || true
fi

# Start fail2ban (requires privileged mode)
if command -v fail2ban-server &> /dev/null; then
    echo "Starting fail2ban..."
    mkdir -p /var/run/fail2ban
    fail2ban-client start 2>/dev/null || true
fi

# List available tools
echo ""
echo "=== Available Defensive Tools ==="
echo "Firewall: iptables, ufw, nftables"
echo "IDS/IPS: suricata, zeek, snort, fail2ban"
echo "HIDS: aide, rkhunter, chkrootkit, wazuh"
echo "Malware: clamav"
echo "Monitoring: tcpdump, tshark, htop, iotop"
echo "Forensics: volatility, sleuthkit, autopsy"
echo "Audit: auditd, lynis"
echo ""

# Start the service
echo "Starting Blue Agent service..."
exec "$@"