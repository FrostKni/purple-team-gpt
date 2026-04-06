# =============================================================================
# Purple Team GPT - Red Agent (Kali Linux) 
# =============================================================================
# Full-featured Kali Linux container with 50+ offensive security tools
# For experimentation and purple team simulations
#
# Build: docker build -t purple-team-red-agent:kali -f docker/red-agent-kali.Dockerfile .
# Run:   docker run -d --name red-agent --privileged purple-team-red-agent:kali
# =============================================================================

FROM kalilinux/kali-rolling:latest

LABEL maintainer="Purple Team GPT"
LABEL description="Red Agent - Full offensive security toolkit"
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
    # System utilities
    sudo \
    vim \
    less \
    file \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - INFORMATION GATHERING
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Network scanning
    nmap \
    masscan \
    # Web reconnaissance
    nikto \
    whatweb \
    wpscan \
    joomscan \
    # DNS enumeration
    dnsenum \
    dnsrecon \
    fierce \
    dnswalk \
    # OSINT
    theharvester \
    recon-ng \
    maltego \
    shodan \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - VULNERABILITY SCANNING
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Web vulnerability scanners
    nuclei \
    zaproxy \
    skipfish \
    # Database assessment
    sqlmap \
    # Network vulnerability
    openvas \
    nessus \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - WEB APPLICATION ATTACKS
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Directory enumeration
    gobuster \
    dirb \
    dirbuster \
    ffuf \
    feroxbuster \
    # Web shells
    weevely \
    # Other web tools
    burpsuite \
    cadaver \
    davtest \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - PASSWORD ATTACKS
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Password cracking
    john \
    john-data \
    hashcat \
    # Online attacks
    hydra \
    medusa \
    ncrack \
    patator \
    # Wordlists
    wordlists \
    cewl \
    crunch \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - EXPLOITATION
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Metasploit Framework
    metasploit-framework \
    # Search exploit database
    exploitdb \
    # Shell generators
    msfpc \
    # Other exploitation
    armitage \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - ACTIVE DIRECTORY / WINDOWS
# =============================================================================
RUN apt-get update && apt-get install -y \
    # AD enumeration
    crackmapexec \
    bloodhound \
    neo4j \
    impacket-scripts \
    # Kerberos
    kerberoast \
    kerbrute \
    rubeus \
    # SMB
    smbclient \
    enum4linux \
    enum4linux-ng \
    smbmap \
    # LDAP
    ldap-utils \
    windapsearch \
    # PowerShell
    powershell \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - WIRELESS
# =============================================================================
RUN apt-get update && apt-get install -y \
    aircrack-ng \
    reaver \
    bully \
    cowpatty \
    fern-wifi-cracker \
    kismet \
    wifite \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - SNIFFING & SPOOFING
# =============================================================================
RUN apt-get update && apt-get install -y \
    wireshark \
    tshark \
    tcpdump \
    ettercap-graphical \
    bettercap \
    mitmproxy \
    responder \
    scapy \
    netsniff-ng \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - REVERSE ENGINEERING
# =============================================================================
RUN apt-get update && apt-get install -y \
    ghidra \
    radare2 \
    binwalk \
    apktool \
    dex2jar \
    jadx \
    ollydbg \
    edb-debugger \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - FORENSICS
# =============================================================================
RUN apt-get update && apt-get install -y \
    autopsy \
    sleuthkit \
    volatility \
    volatility3 \
    foremost \
    scalpel \
    steghide \
    stegsolve \
    exiftool \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - POST-EXPLOITATION
# =============================================================================
RUN apt-get update && apt-get install -y \
    # Empire
    powershell-empire \
    starkiller \
    # C2 frameworks
    covenant-kbx \
    sliver \
    # Pivoting
    proxychains4 \
    sshuttle \
    chisel \
    ligolo \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# OFFENSIVE TOOLS - ADDITIONAL (GO/PIP INSTALLS)
# =============================================================================
# Install Go for modern tools
RUN apt-get update && apt-get install -y golang-go && rm -rf /var/lib/apt/lists/*
ENV GOPATH=/go
ENV PATH=$PATH:/go/bin

# Install modern Go-based tools
RUN go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest && \
    go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest && \
    go install -v github.com/projectdiscovery/katana/cmd/katana@latest && \
    go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest && \
    go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@latest && \
    go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest && \
    go install -v github.com/owasp-amass/amass/v4/...@latest && \
    go install -v github.com/ffuf/ffuf/v2@latest && \
    go install -v github.com/tomnomnom/assetfinder@latest && \
    go install -v github.com/tomnomnom/httprobe@latest && \
    go install -v github.com/tomnomnom/waybackurls@latest && \
    go install -v github.com/tomnomnom/gf@latest && \
    go install -v github.com/michenriksen/aquatone@latest && \
    go install -v github.com/hakluke/hakrawler@latest && \
    go install -v github.com/lc/gau/v2/cmd/gau@latest && \
    go install -v github.com/hahwul/dalfox/v2@latest && \
    go install -v github.com/dwisiswant0/tuhhng@latest && \
    go install -v github.com/ropnop/kerbrute@latest && \
    go install -v github.com/ropnop/go_windapsearch@latest && \
    go install -v github.com/bp0lr/gauplus@latest && \
    go install -v github.com/jaeles-project/jaeles@latest && \
    go install -v github.com/madwireng/grype@latest || true

# Install Rust tools
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install rustscan --locked && \
    cargo install hyperfine && \
    cargo install ripgrep && \
    cargo install fd-find || true

# =============================================================================
# PYTHON SECURITY TOOLS (PIP)
# =============================================================================
RUN pip3 install --no-cache-dir \
    # Attack frameworks
    pwntools \
    pexpect \
    paramiko \
    # Web
    requests \
    beautifulsoup4 \
    lxml \
    # Specific tools
    impacket \
    pwncat \
    pypykatz \
    aiocron \
    colorama \
    rich \
    # Nuclei templates
    nuclei-templates || true

# =============================================================================
# WORDLISTS & RESOURCES
# =============================================================================
# Extract wordlists
RUN gunzip -k /usr/share/wordlists/rockyou.txt.gz 2>/dev/null || true
RUN ln -sf /usr/share/seclists /opt/seclists 2>/dev/null || true

# Create tool directories
RUN mkdir -p /opt/tools /opt/wordlists /opt/payloads /opt/loot

# =============================================================================
# PYTHON APPLICATION SETUP
# =============================================================================
# Create virtual environment for the application
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV=/opt/venv

# Install Python dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction || pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    pydantic-settings \
    python-dotenv \
    httpx \
    websockets \
    chromadb \
    sqlmodel \
    openai \
    anthropic \
    litellm \
    paramiko \
    structlog \
    aiosqlite \
    tenacity \
    jinja2 \
    pyyaml \
    rich

# =============================================================================
# APPLICATION CODE
# =============================================================================
COPY src/purple_team_gpt/ ./src/purple_team_gpt/
COPY scripts/red_arsenal/ ./scripts/red_arsenal/ 2>/dev/null || true
COPY config/tools_registry.json ./config/tools_registry.json 2>/dev/null || true

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV AGENT_TYPE=red
ENV AGENT_HOST=0.0.0.0
ENV AGENT_PORT=8000

# Create necessary directories
RUN mkdir -p /var/log/purple-team /tmp/purple-team

# =============================================================================
# HEALTH CHECK & EXPOSE
# =============================================================================
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# =============================================================================
# ENTRYPOINT
# =============================================================================
# Copy and set up entrypoint
COPY docker/entrypoint-red.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "purple_team_gpt.services.red_agent_service.main"]