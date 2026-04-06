# Purple Team GPT - DevOps Setup Guide

This document describes the complete DevOps setup for Purple Team GPT.

## Quick Start

```bash
# Development
./dev.sh              # Start development environment
./dev.sh --build      # Force rebuild
./dev.sh --clean      # Clean and rebuild

# Production
./start.sh            # Start production environment
./start.sh --health   # Run health checks

# Stop all services
./scripts/stop.sh
```

## Docker Setup

### Services

| Service | Port | Description |
|---------|------|-------------|
| Backend | 8000 | FastAPI application |
| Frontend | 3000/5173 | React/Vite application |
| ChromaDB | 8001 | Vector database |
| Redis | 6379 | Rate limiting & caching |
| Ollama | 11434 | Local LLM (optional) |

### Dockerfiles

- `docker/Dockerfile.backend` - Multi-stage build for Python/FastAPI
- `docker/Dockerfile.frontend` - Multi-stage build for React/Vite

### Docker Compose Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base configuration |
| `docker-compose.dev.yml` | Development overrides |
| `docker-compose.prod.yml` | Production overrides |

### Usage

```bash
# Development (with hot reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With Ollama
docker-compose --profile ollama up -d
```

## CI/CD Pipeline

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to main | Lint, test, build |
| `cd.yml` | Push to main | Deploy to staging |
| `security.yml` | Daily + PR | Security scanning |

### CI Pipeline

1. **Backend Lint** - Ruff, Black, MyPy
2. **Backend Test** - Pytest with coverage
3. **Frontend Lint** - ESLint, TypeScript
4. **Frontend Build** - Vite production build
5. **Security Scan** - Trivy, Bandit
6. **Docker Build** - Image build test

### CD Pipeline

1. **Build** - Build and push Docker images to GHCR
2. **Deploy Staging** - Automatic on main merge
3. **Deploy Production** - Manual trigger required

### Secrets Required

Configure these in GitHub repository secrets:

```
APP_SECRET_KEY
LLM_OPENAI_API_KEY
STAGING_HOST
STAGING_USER
STAGING_SSH_KEY
STAGING_URL
PRODUCTION_HOST
PRODUCTION_USER
PRODUCTION_SSH_KEY
PRODUCTION_URL
REDIS_PASSWORD
VITE_API_URL
VITE_WS_URL
```

## Environment Configuration

### Files

| File | Purpose |
|------|---------|
| `.env.example` | Template with all options |
| `config/environments/development.env` | Development defaults |
| `config/environments/staging.env` | Staging environment |
| `config/environments/production.env` | Production template |

### Required Variables

```bash
APP_SECRET_KEY=your-secret-key-min-32-chars
LLM_OPENAI_API_KEY=sk-your-api-key
```

### Secrets Management

**Production Recommendations:**

1. **AWS** - Use AWS Secrets Manager + Parameter Store
2. **Azure** - Use Azure Key Vault
3. **GCP** - Use Secret Manager
4. **Kubernetes** - Use Kubernetes Secrets + External Secrets Operator
5. **Docker Swarm** - Use Docker Secrets

**Key Security Practices:**

- Never commit .env files
- Rotate secrets every 90 days
- Use different secrets per environment
- Audit secret access logs
- Use secret scanning (Gitleaks, TruffleHog)

## Startup Scripts

### dev.sh

Development environment startup with:
- Environment validation
- Service health checks
- Hot reload enabled
- Debug port exposed (5678)

### start.sh

Production startup with:
- Required variable validation
- Backup option
- Health verification
- Startup logging

### scripts/health-check.sh

Comprehensive health monitoring for all services.

### scripts/backup.sh

Creates timestamped backups of:
- ChromaDB data
- Redis data
- Feedback database
- Configuration

### scripts/restore.sh

Restores data from backup files.

## Makefile Commands

```bash
make help          # Show all commands
make dev           # Start development
make start         # Start production
make stop          # Stop all services
make health        # Run health checks
make test          # Run tests
make lint          # Run linters
make backup        # Create backup
make restore       # Restore from backup
```

## Health Checks

All services include health checks:

| Service | Check | Interval |
|---------|-------|----------|
| Backend | GET /health | 30s |
| Frontend | GET /health | 30s |
| ChromaDB | GET /api/v1/heartbeat | 30s |
| Redis | redis-cli ping | 30s |

## Monitoring

Access points:

- Backend API: http://localhost:8000/docs
- Backend Health: http://localhost:8000/health
- Backend Status: http://localhost:8000/status
- Frontend: http://localhost:3000

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Database issues

```bash
# Reset ChromaDB
docker-compose down -v
docker-compose up -d chromadb
```

### Redis connection issues

```bash
# Test Redis connection
docker exec -it purple-team-redis redis-cli ping
```

### Clean everything

```bash
./dev.sh --clean
# or
make clean
```

## File Structure

```
purple-team-gpt/
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── .github/workflows/
│   ├── ci.yml
│   ├── cd.yml
│   └── security.yml
├── config/environments/
│   ├── development.env
│   ├── staging.env
│   └── production.env
├── scripts/
│   ├── health-check.sh
│   ├── backup.sh
│   ├── restore.sh
│   └── stop.sh
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.example
├── .dockerignore
├── dev.sh
├── start.sh
└── Makefile
```