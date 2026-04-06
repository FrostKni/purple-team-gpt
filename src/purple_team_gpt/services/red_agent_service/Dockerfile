# Red Agent Service Dockerfile
FROM kalilinux/kali-rolling:latest

WORKDIR /app

# Install system dependencies and security tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    nmap \
    nikto \
    gobuster \
    sqlmap \
    hydra \
    ncrack \
    enum4linux \
    smbclient \
    curl \
    dnsutils \
    whois \
    whatweb \
    dirb \
    ffuf \
    nuclei \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction

# Copy source code
COPY src/ ./src/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV AGENT_TYPE=red

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run service
CMD ["python", "-m", "purple_team_gpt.services.red_agent_service.main"]