# Purple Team GPT Quick Start Guide

> **Time to first assessment: ~10 minutes with Docker**

This guide will get you from zero to running your first cybersecurity simulation in the fastest way possible.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start with Docker](#quick-start-with-docker)
- [Local Development Setup](#local-development-setup)
- [Running Your First Assessment](#running-your-first-assessment)
- [Configuration Options](#configuration-options)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Prerequisites

### Required

| Tool | Version | Purpose | Verification |
|------|---------|---------|--------------|
| **Docker** | 24.0+ | Container runtime | `docker --version` |
| **Docker Compose** | 2.20+ | Multi-container orchestration | `docker compose version` |
| **LLM API Key** | - | AI agent intelligence | See [LLM Providers](#llm-providers) |

### For Local Development (Optional)

| Tool | Version | Purpose | Verification |
|------|---------|---------|--------------|
| **Python** | 3.11+ | Backend runtime | `python --version` |
| **Node.js** | 18+ | Frontend build | `node --version` |
| **npm** | 9+ | Package management | `npm --version` |
| **PostgreSQL** | 16+ | Primary database (or use Docker) | `psql --version` |
| **Redis** | 7.2+ | Caching (or use Docker) | `redis-cli --version` |

### LLM Providers

You need at least **one** LLM API key:

| Provider | Models | Get API Key | Cost |
|----------|--------|-------------|------|
| **OpenAI** | GPT-4o, GPT-4-turbo, GPT-3.5-turbo | [platform.openai.com](https://platform.openai.com/api-keys) | $$ |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus | [console.anthropic.com](https://console.anthropic.com/) | $$ |
| **Groq** | Llama 3, Mixtral | [console.groq.com](https://console.groq.com/keys) | Free tier available |
| **DeepSeek** | DeepSeek Chat, Coder | [platform.deepseek.com](https://platform.deepseek.com/) | $ |
| **Mistral** | Mistral Large, Medium, Small | [console.mistral.ai](https://console.mistral.ai/) | $ |
| **Ollama** | Llama 3.2, Mistral, etc. | [ollama.ai](https://ollama.ai) | Free (local) |

> **Recommended for beginners**: Start with OpenAI GPT-4o or Anthropic Claude 3.5 Sonnet for best results.

---

## Quick Start with Docker

The fastest way to get started. Docker handles all dependencies automatically.

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/purple-team-gpt.git
cd purple-team-gpt
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your API key (REQUIRED)
nano .env  # or use your preferred editor
```

**Minimum required configuration in `.env`:**

```env
# Set at least one LLM API key
LLM_OPENAI_API_KEY=sk-proj-your-key-here
# OR
LLM_ANTHROPIC_API_KEY=sk-ant-your-key-here

# Change these for production!
APP_SECRET_KEY=generate-a-secure-random-key-at-least-64-characters-long
DB_PASSWORD=your-secure-database-password
```

> **Security Warning**: Never commit your `.env` file to version control. It's already in `.gitignore`.

### Step 3: Generate Secrets (Production)

For production deployments, generate secure secrets:

```bash
./scripts/generate-secrets.sh -o .env.production
```

Then update your `.env` with the generated values.

### Step 4: Start Services

```bash
# Start all services
docker compose up -d

# Watch logs (optional)
docker compose logs -f
```

**Services started:**

| Service | Port | Purpose |
|---------|------|---------|
| **nginx** | 80, 443 | Reverse proxy with SSL |
| **backend** | 8000 (internal) | FastAPI application |
| **frontend** | 80 (internal) | React web UI |
| **postgres** | 5432 (internal) | Primary database |
| **redis** | 6379 (internal) | Caching & rate limiting |
| **chromadb** | 8000 (internal) | Vector database |

### Step 5: Verify Installation

```bash
# Check all services are healthy
docker compose ps

# Test backend health
curl http://localhost:8000/health

# Expected response: {"status": "healthy", ...}
```

### Step 6: Access the Application

Open your browser:

- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Step 7: Create Your Account

#### Option A: Via API

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePassword123!",
    "username": "admin"
  }'

# Login to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=SecurePassword123!"
```

#### Option B: Via Web UI

1. Navigate to http://localhost:3000
2. Click "Register"
3. Enter your credentials
4. Login with your new account

---

## Local Development Setup

For developers who want to modify the codebase.

### Backend Setup

#### Step 1: Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# OR
.\.venv\Scripts\activate   # Windows
```

#### Step 2: Install Dependencies

```bash
# Install package in development mode with all extras
pip install -e ".[dev,full]"
```

#### Step 3: Configure Environment

```bash
cp .env.example .env
nano .env  # Add your LLM API keys
```

#### Step 4: Start Infrastructure Services

You can run just the databases with Docker:

```bash
# Start only PostgreSQL, Redis, and ChromaDB
docker compose up -d postgres redis chromadb
```

Or install them locally:

```bash
# PostgreSQL
sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian
brew install postgresql@16                       # macOS

# Redis
sudo apt install redis-server  # Ubuntu/Debian
brew install redis             # macOS

# ChromaDB (run in Docker for simplicity)
docker run -d --name chromadb -p 8001:8000 chromadb/chroma:0.4.24
```

#### Step 5: Run Database Migrations

```bash
# Apply migrations
alembic upgrade head

# Verify tables created
python -c "from purple_team_gpt.core.database import engine; print(engine.table_names())"
```

#### Step 6: Start Development Server

```bash
# Start with auto-reload
uvicorn purple_team_gpt.backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Frontend Setup

#### Step 1: Navigate to Frontend Directory

```bash
cd src/frontend
```

#### Step 2: Install Dependencies

```bash
npm install
```

#### Step 3: Configure API URL

Create `.env.local` if needed:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

#### Step 4: Start Development Server

```bash
npm run dev
```

The frontend will be available at http://localhost:5173

### Full Development Stack

Run both backend and frontend in development mode:

```bash
# Terminal 1: Backend
source .venv/bin/activate
uvicorn purple_team_gpt.backend.main:app --reload

# Terminal 2: Frontend
cd src/frontend && npm run dev

# Terminal 3: Infrastructure (optional, if not running via Docker)
# PostgreSQL, Redis, ChromaDB as needed
```

---

## Running Your First Assessment

### Via Web UI

#### Step 1: Create a Session

1. Login to the web UI at http://localhost:3000
2. Navigate to **"New Session"** or **"Attack"** tab
3. Configure your target:

| Field | Example | Description |
|-------|---------|-------------|
| **Target** | `192.168.1.100` | IP or hostname of your authorized target |
| **Attack Type** | `reconnaissance` | Type of assessment |
| **Safe Mode** | `Enabled` | Prevents destructive operations |

#### Step 2: Start the Assessment

1. Click **"Start Assessment"**
2. Watch the live dashboard:
   - **Red Agent Log**: Offensive operations in real-time
   - **Blue Agent Log**: Defensive detection and response
   - **Findings Panel**: Discovered vulnerabilities

#### Step 3: Monitor Progress

The dashboard shows:

- **Progress bar**: Overall completion percentage
- **Step count**: X of max_steps completed
- **Duration**: Time elapsed
- **Status**: running, paused, completed, or error

#### Step 4: Review Results

After completion:

1. Navigate to **"Results"** tab
2. Review findings by severity (Critical, High, Medium, Low)
3. See agent performance metrics
4. Export report (PDF, JSON, or HTML)

#### Step 5: Provide Feedback (Optional)

Rate agent decisions to improve future performance:

1. Find a specific action in the logs
2. Click the **feedback** icon
3. Rate 1-5 stars
4. Add optional comment
5. Submit

### Via API

```bash
# Step 1: Get authentication token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=SecurePassword123!" \
  | jq -r '.access_token')

# Step 2: Create a session
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/v1/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "192.168.1.100",
    "attack_type": "reconnaissance",
    "config": {
      "safe_mode": true,
      "max_steps": 20
    }
  }' \
  | jq -r '.id')

# Step 3: Start the assessment
curl -X POST "http://localhost:8000/api/v1/sessions/$SESSION_ID/start" \
  -H "Authorization: Bearer $TOKEN"

# Step 4: Monitor via WebSocket
wscat -c "ws://localhost:8000/ws/session/$SESSION_ID" \
  -H "Authorization: Bearer $TOKEN"

# Step 5: Get results
curl -s "http://localhost:8000/api/v1/sessions/$SESSION_ID/metrics" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

### Via CLI

```bash
# Ensure CLI is installed
pip install -e ".[full]"

# Start a reconnaissance assessment
purple-team attack --target 192.168.1.100 --type recon --safe-mode

# Run full purple team exercise
purple-team exercise --target 192.168.1.100 --duration 60m

# Export results for fine-tuning
purple-team export --rating 4+ --format jsonl --output training_data.jsonl
```

---

## Configuration Options

### LLM Provider Configuration

Configure multiple providers for automatic failover:

```env
# Default provider (used first)
LLM_DEFAULT_PROVIDER=openai
LLM_DEFAULT_MODEL=gpt-4o

# Primary provider
LLM_OPENAI_API_KEY=sk-proj-xxxxx

# Fallback providers (used if primary fails)
LLM_ANTHROPIC_API_KEY=sk-ant-xxxxx
LLM_GROQ_API_KEY=gsk-xxxxx
LLM_DEEPSEEK_API_KEY=sk-xxxxx
LLM_MISTRAL_API_KEY=xxxxx

# Local LLM (no API key needed)
LLM_OLLAMA_BASE_URL=http://localhost:11434

# Enable automatic failover
LLM_ENABLE_FAILOVER=true
```

**Failover Order:**
```
OpenAI → Anthropic → Groq → DeepSeek → Mistral → Ollama
```

### Agent Configuration

Fine-tune agent behavior:

```env
# Maximum steps before stopping
AGENT_MAX_STEPS=50

# Timeout per step (seconds)
AGENT_TIMEOUT=300

# Safe mode (recommended for beginners)
AGENT_SAFE_MODE=true

# Auto-confirm destructive actions (DANGEROUS!)
AGENT_AUTO_CONFIRM=false
```

### Security Configuration

```env
# Application settings
APP_ENV=production          # development, staging, production
APP_DEBUG=false             # MUST be false in production
APP_LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Rate limiting
APP_RATE_LIMIT_REQUESTS=100
APP_RATE_LIMIT_WINDOW_SECONDS=60

# CORS (comma-separated origins)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### Database Configuration

```env
# PostgreSQL
DB_HOST=postgres
DB_PORT=5432
DB_NAME=purple_team_gpt
DB_USER=postgres
DB_PASSWORD=your-secure-password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_PERSIST_DIR=/app/data/chromadb
```

### Frontend Configuration

```env
# Backend API URL
VITE_API_URL=https://your-domain.com
VITE_WS_URL=wss://your-domain.com
```

---

## Troubleshooting

### Docker Issues

#### Services won't start

```bash
# Check service status
docker compose ps

# View logs for specific service
docker compose logs backend
docker compose logs postgres

# Restart all services
docker compose down && docker compose up -d

# Force rebuild
docker compose up -d --build --force-recreate
```

#### Port conflicts

```bash
# Check what's using the port
lsof -i :3000
lsof -i :8000

# Stop conflicting services
sudo systemctl stop nginx  # If nginx is using port 80
```

#### Volume/permission issues

```bash
# Fix permissions
sudo chown -R $USER:$USER ./data ./logs ./secrets

# Reset volumes (WARNING: destroys data)
docker compose down -v
docker compose up -d
```

### Database Issues

#### PostgreSQL connection errors

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Test connection
docker compose exec postgres psql -U postgres -d purple_team_gpt

# Reset database (WARNING: destroys data)
docker compose down -v
docker compose up -d postgres
alembic upgrade head
```

#### Migration errors

```bash
# Check current migration status
alembic current

# Rollback last migration
alembic downgrade -1

# Reset to clean state
alembic downgrade base
alembic upgrade head
```

### LLM API Errors

#### Invalid API key

```bash
# Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Verify environment variable is set
docker compose exec backend env | grep LLM
```

#### Rate limiting

```bash
# Check for rate limit errors in logs
docker compose logs backend | grep -i "rate limit"

# Solution: Use multiple providers with failover enabled
LLM_ENABLE_FAILOVER=true
```

#### Timeout errors

```bash
# Increase timeout
AGENT_TIMEOUT=600  # 10 minutes

# Use faster model
LLM_DEFAULT_MODEL=gpt-3.5-turbo  # Instead of gpt-4o
```

### ChromaDB Issues

#### Connection refused

```bash
# Check ChromaDB is healthy
docker compose ps chromadb

# Test ChromaDB directly
curl http://localhost:8001/api/v1/heartbeat

# Restart ChromaDB
docker compose restart chromadb
```

#### Embedding errors

```bash
# Clear ChromaDB cache (WARNING: loses learned patterns)
docker compose exec backend python -c "
from purple_team_gpt.core.rag.vector_store import VectorStore
vs = VectorStore()
vs.reset()
"
```

### Frontend Issues

#### Build errors

```bash
# Clear npm cache
cd src/frontend
rm -rf node_modules package-lock.json
npm install

# Rebuild
npm run build
```

#### API connection errors

```bash
# Check frontend can reach backend
curl http://localhost:8000/health

# Verify CORS settings
# In .env:
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Authentication Issues

#### JWT token expired

```bash
# Get new token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=SecurePassword123!"

# Increase token expiration (in .env)
APP_JWT_EXPIRE_MINUTES=1440  # 24 hours
```

#### Password reset

```bash
# Direct database reset (development only!)
docker compose exec postgres psql -U postgres -d purple_team_gpt -c \
  "UPDATE users SET password_hash='new_bcrypt_hash' WHERE email='admin@example.com';"
```

### Performance Issues

#### High memory usage

```bash
# Check resource usage
docker stats

# Limit container resources (in docker-compose.yml)
deploy:
  resources:
    limits:
      memory: 2G
```

#### Slow responses

```bash
# Enable Redis caching
REDIS_HOST=redis
REDIS_PORT=6379

# Use faster LLM model
LLM_DEFAULT_MODEL=gpt-3.5-turbo
# Or use Groq (fastest inference)
LLM_DEFAULT_PROVIDER=groq
LLM_DEFAULT_MODEL=llama-3.1-70b-versatile
```

---

## Next Steps

Now that you're up and running, explore these resources:

### Documentation

| Document | Description |
|----------|-------------|
| [Architecture](ARCHITECTURE.md) | Deep dive into system architecture |
| [API Reference](API.md) | Complete API documentation |
| [Implementation Plan](IMPLEMENTATION_PLAN.md) | Development roadmap |
| [Secrets Management](SECRETS_MANAGEMENT.md) | Security best practices |

### Learn the System

1. **Try different attack types**: `recon`, `vulnerability_scan`, `exploitation`
2. **Experiment with LLM providers**: Compare results across models
3. **Provide feedback**: Rate agent decisions to improve performance
4. **Export training data**: Generate fine-tuning datasets from high-quality runs

### Join the Community

| Channel | Link |
|---------|------|
| GitHub Issues | [Report bugs, request features](https://github.com/your-org/purple-team-gpt/issues) |
| Discussions | [Ask questions, share ideas](https://github.com/your-org/purple-team-gpt/discussions) |

### Production Deployment

For production deployments, see:

- [Distributed Setup Guide](DISTRIBUTED_SETUP.md)
- [Security Hardening](security/README.md)
- [SSL/TLS Configuration](../secrets/README.md)

---

## Quick Reference

### Essential Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down

# Restart a service
docker compose restart backend

# Check health
curl http://localhost:8000/health

# Run tests
pytest tests/ -v

# Start local development
uvicorn purple_team_gpt.backend.main:app --reload
```

### Environment Variables Checklist

- [ ] `LLM_OPENAI_API_KEY` or other LLM key set
- [ ] `APP_SECRET_KEY` changed from default (64+ chars)
- [ ] `DB_PASSWORD` changed from default
- [ ] `APP_DEBUG=false` in production
- [ ] `AGENT_SAFE_MODE=true` for initial runs

### Support

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Search [existing issues](https://github.com/your-org/purple-team-gpt/issues)
3. Open a [new issue](https://github.com/your-org/purple-team-gpt/issues/new) with:
   - Error message and logs
   - Steps to reproduce
   - Environment details (OS, Docker version, etc.)

---

**Happy testing! Remember: Only test targets you own or have explicit authorization.**
