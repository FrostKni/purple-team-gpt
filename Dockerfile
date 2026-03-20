# Purple Team GPT - Backend Dockerfile
# Multi-stage build for optimized production image

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install security tools and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Security tools
    nmap \
    nikto \
    curl \
    # Build dependencies for Python packages
    build-essential \
    # Network utilities
    iputils-ping \
    netcat-openbsd \
    # SSL support
    ca-certificates \
    # Git for some package installations
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml ./

# Create requirements from pyproject.toml and install
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/
COPY data/ ./data/

# Create necessary directories and set permissions
RUN mkdir -p /app/data/chromadb \
    && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run FastAPI with uvicorn
CMD ["uvicorn", "purple_team_gpt.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]