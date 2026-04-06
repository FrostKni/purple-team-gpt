# =============================================================================
# Purple Team GPT - Orchestrator Service
# =============================================================================
# Central coordination service for Purple Team simulations
#
# Build: docker build -t purple-team-orchestrator:latest -f docker/orchestrator.Dockerfile .
# Run:   docker run -d --name orchestrator -p 8000:8000 purple-team-orchestrator:latest
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="Purple Team GPT"
LABEL description="Orchestrator - Central coordination service"
LABEL version="1.0.0"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

WORKDIR /app

# =============================================================================
# SYSTEM DEPENDENCIES
# =============================================================================
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    # For SQLite
    sqlite3 \
    # For networking
    netcat-openbsd \
    iputils-ping \
    # For SSL
    openssl \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# PYTHON DEPENDENCIES
# =============================================================================
# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV=/opt/venv

# Install Python dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction || pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pydantic \
    pydantic-settings \
    python-dotenv \
    python-multipart \
    httpx \
    websockets \
    aiohttp \
    chromadb \
    sqlmodel \
    aiosqlite \
    openai \
    anthropic \
    litellm \
    structlog \
    rich \
    tenacity \
    jinja2 \
    pyyaml \
    python-jose[cryptography] \
    passlib[bcrypt] \
    redis \
    celery \
    flower

# =============================================================================
# APPLICATION CODE
# =============================================================================
COPY src/purple_team_gpt/ ./src/purple_team_gpt/
COPY config/ ./config/ 2>/dev/null || true

# =============================================================================
# CONFIGURATION
# =============================================================================
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONFAULTHANDLER=1

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/reports

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["python", "-m", "purple_team_gpt.backend.main"]