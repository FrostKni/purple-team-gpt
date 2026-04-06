# =============================================================================
# Purple Team GPT - Blue Agent (Ubuntu Server)
# =============================================================================
# Full-featured Ubuntu Server container with 50+ defensive security tools
# For experimentation and purple team simulations
#
# Build: docker build -t purple-team-blue-agent:ubuntu -f docker/blue-agent-ubuntu.Dockerfile .
# Run:   docker run -d --name blue-agent --privileged purple-team-blue-agent:ubuntu
# =============================================================================

FROM ubuntu:22.04

LABEL maintainer="Purple Team GPT"
LABEL description="Blue Agent - Full defensive security toolkit"
LABEL version="1.0.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

WORKDIR /app

# =============================================================================
# CORE SYSTEM SETUP
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Build essentials
    build-essential \
    cmake \
    git \
    wget \
    curl \
    unzip \
    tar \
    gzip \
    software-properties-common \
    apt-transport-https \
    gnupg \
    lsb-release \
    # Python
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    # Networking
    net-tools \
    iputils-ping \
    iproute2 \
    dnsutils \
    whois \
    ethtool \
    iftop \
    nethogs \
    # System utilities
    sudo \
    vim \
    less \
    file \
    procps \
    htop \
    iotop \
    sysstat \
    strace \
    ltrace \
    lsof \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# DEFENSIVE TOOLS - FIREWALL & NETWORK SECURITY
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Firewalls
    iptables \
    iptables-persistent \
    ufw \
    nftables \
    firewalld \
    # Network monitoring
    ntopng \
    suricata \
    zeek \
    snort \
    # IDS/IPS
    fail2ban \
    psad \
    portsentry \
    # Network analysis
    tcpdump \
    tshark \
    wireshark-common \
    termshark \
    # DNS security
    dnsmasq \
    unbound \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# DEFENSIVE TOOLS - HOST-BASED SECURITY
# =============================================================================
RUN apt-get update && apt-get install -y \
    # HIDS
    aide \
    aide-common \
    samhain \
    ossec-hids-server \
    ossec-hids-agent \
    # Wazuh (requires repo)
    # Rootkit detection
    rkhunter \
    chkrootkit \
    # Malware scanning
    clamav \
    clamav-daemon \
    clamav-freshclam \
    # File integrity
    inotify-tools \
    iwatch \
    # Audit
    auditd \
    audispd-plugins \
    # AppArmor/SELinux
    apparmor \
    apparmor-utils \
    apparmor-profiles \
    apparmor-profiles-extra \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# DEFENSIVE TOOLS - LOGGING & MONITORING
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Log management
    rsyslog \
    rsyslog-gnutls \
    logrotate \
    logwatch \
    logcheck \
    # Monitoring
    prometheus-node-exporter \
    grafana-agent \
    # ELK stack components
    elasticsearch \
    logstash \
    kibana \
    filebeat \
    # Journal
    systemd-journal-remote \
    # SIEM tools
    wazuh-manager \
    && rm -rf /var/lib/apt/lists/* || true

# =============================================================================
# DEFENSIVE TOOLS - CONTAINER SECURITY
# =============================================================================
RUN apt-get update && apt-get install -y \
    docker.io \
    containerd \
    # Container scanning
    trivy \
    # Container runtime security
    falco \
    # Docker security
    docker-bench-security \
    && rm -rf /var/lib/apt/lists/* || true

# =============================================================================
# DEFENSIVE TOOLS - CLOUD SECURITY
# =============================================================================
RUN apt-get update && apt-get install -y \
    # AWS CLI
    awscli \
    # Azure CLI
    azure-cli \
    # GCloud CLI
    google-cloud-sdk \
    # Terraform security
    checkov \
    tfsec \
    terrascan \
    && rm -rf /var/lib/apt/lists/* || true

# =============================================================================
# DEFENSIVE TOOLS - VULNERABILITY MANAGEMENT
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Vulnerability scanners
    openvas-scanner \
    openvas-manager \
    greenbone-security-assistant \
    # CVE tools
    cve-checker \
    # Dependency scanning
    dependency-check \
    safety \
    # Security benchmarks
    lynis \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# DEFENSIVE TOOLS - AUTHENTICATION & ACCESS
# =============================================================================
RUN apt-get update && apt-get install -y \
    # SSH hardening
    ssh-audit \
    fail2ban \
    # 2FA
    libpam-google-authenticator \
    # Kerberos
    krb5-kdc \
    krb5-admin-server \
    # LDAP
    slapd \
    ldap-utils \
    # Certification
    openssl \
    easy-rsa \
    # Password policies
    libpam-cracklib \
    libpam-pwquality \
    cracklib-runtime \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# DEFENSIVE TOOLS - FORENSICS
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Disk forensics
    sleuthkit \
    autopsy \
    guymager \
    # Memory forensics
    volatility \
    volatility3 \
    # File carving
    foremost \
    scalpel \
    # Memory acquisition
    lime \
    # Timeline
    plaso \
    # Hash tools
    hashdeep \
    md5deep \
    # Metadata
    exiftool \
    # Disk imaging
    dc3dd \
    dcfldd \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# DEFENSIVE TOOLS - THREAT INTELLIGENCE
# =============================================================================
RUN apt-get update && apt-get install -y \
    # MISP
    misp \
    # YARA
    yara \
    python3-yara \
    # Threat feeds
    threatfox \
    # IOC tools
    ioc_parser \
    && rm -rf /var/lib/apt/lists/* || true

# =============================================================================
# DEFENSIVE TOOLS - ENCRYPTION
# =============================================================================
RUN apt-get update && apt-get install -y \
    gnupg2 \
    gnupg-agent \
    scdaemon \
    pcscd \
    cryptsetup \
    luks-tools \
    keyrings \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# DEFENSIVE TOOLS - AUTOMATION & ORCHESTRATION
# =============================================================================
RUN apt-get update && apt-get install -y \
    ansible \
    ansible-core \
    terraform \
    packer \
    vagrant \
    jq \
    yq \
    # SOAR
    shuffle \
    # Incident response
    grr-server \
    grr-client \
    velociraptor \
    && rm -rf /var/lib/apt/lists/* || true

# =============================================================================
# DEFENSIVE TOOLS - ADDITIONAL (PIP/GO INSTALLS)
# =============================================================================
# Install Go for modern tools
RUN apt-get update && apt-get install -y golang-go && rm -rf /var/lib/apt/lists/*
ENV GOPATH=/go
ENV PATH=$PATH:/go/bin

# Install Go-based security tools
RUN go install -v github.com/aquasecurity/trivy/cmd/trivy@latest && \
    go install -v github.com/aquasecurity/tfsec/cmd/tfsec@latest && \
    go install -v github.com/aquasecurity/checkov/cmd/checkov@latest || true && \
    go install -v github.com/bridgecrewio/yor/src/yor@latest && \
    go install -v github.com/owasp-amass/amass/v4/...@latest && \
    go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest && \
    go install -v github.com/mikefarah/yq/v4@latest && \
    go install -v github.com/ffuf/ffuf/v2@latest && \
    go install -v github.com/crowdsecurity/crowdsec/cmd/crowdsec@latest && \
    go install -v github.com/crowdsecurity/crowdsec/cmd/crowdsec-cli@latest || true

# Install Rust tools
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install ripgrep && \
    cargo install fd-find && \
    cargo install hyperfine && \
    cargo install bandwhich || true

# =============================================================================
# PYTHON SECURITY TOOLS (PIP)
# =============================================================================
RUN pip3 install --no-cache-dir \
    # Security frameworks
    pysecurity \
    # Monitoring
    prometheus-client \
    psutil \
    # YARA
    yara-python \
    # Network
    scapy \
    dpkt \
    pyshark \
    # Forensics
    volatility3 \
    libforensicstore \
    # Cloud
    boto3 \
    azure-mgmt-security \
    google-cloud-security-center \
    # Logging
    structlog \
    # Automation
    ansible-runner \
    # Defense
    fail2ban \
    # Monitoring
    datadog \
    newrelic \
    sentry-sdk \
    # SSH
    paramiko \
    # Web
    fastapi \
    uvicorn \
    httpx \
    websockets \
    # Data
    pydantic \
    pydantic-settings \
    sqlmodel \
    aiosqlite \
    # LLM
    openai \
    anthropic \
    litellm \
    # Vector DB
    chromadb \
    # Utils
    python-dotenv \
    rich \
    tenacity \
    jinja2 \
    pyyaml

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
# Configure auditd
RUN mkdir -p /etc/audit/rules.d && \
    echo '-w /etc/passwd -p wa -k identity' > /etc/audit/rules.d/identity.rules && \
    echo '-w /etc/shadow -p wa -k identity' >> /etc/audit/rules.d/identity.rules && \
    echo '-w /etc/sudoers -p wa -k sudo' >> /etc/audit/rules.d/identity.rules && \
    echo '-w /var/log/auth.log -p wa -k logins' >> /etc/audit/rules.d/logins.rules && \
    echo '-a exit,always -F arch=b64 -S execve -k exec' >> /etc/audit/rules.d/exec.rules

# Configure rkhunter
RUN rkhunter --update 2>/dev/null || true

# Update clamav
RUN freshclam 2>/dev/null || true

# Configure fail2ban
RUN mkdir -p /etc/fail2ban/jail.d && \
    echo '[sshd]' > /etc/fail2ban/jail.d/sshd.local && \
    echo 'enabled = true' >> /etc/fail2ban/jail.d/sshd.local && \
    echo 'maxretry = 3' >> /etc/fail2ban/jail.d/sshd.local && \
    echo 'bantime = 3600' >> /etc/fail2ban/jail.d/sshd.local

# =============================================================================
# PYTHON APPLICATION SETUP
# =============================================================================
# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV=/opt/venv

# Install application dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction || true

# =============================================================================
# APPLICATION CODE
# =============================================================================
COPY src/purple_team_gpt/ ./src/purple_team_gpt/
COPY scripts/blue_arsenal/ ./scripts/blue_arsenal/ 2>/dev/null || true
COPY config/tools_registry.json ./config/tools_registry.json 2>/dev/null || true

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV AGENT_TYPE=blue
ENV AGENT_HOST=0.0.0.0
ENV AGENT_PORT=8000

# Create necessary directories
RUN mkdir -p /var/log/purple-team /tmp/purple-team /var/lib/aide

# Initialize AIDE database
RUN aideinit 2>/dev/null || true

# =============================================================================
# HEALTH CHECK & EXPOSE
# =============================================================================
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# =============================================================================
# ENTRYPOINT
# =============================================================================
COPY docker/entrypoint-blue.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "purple_team_gpt.services.blue_agent_service.main"]