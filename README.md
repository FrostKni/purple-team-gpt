# Purple Team GPT

**Autonomous Purple Team Cybersecurity Simulation Framework**

An AI-powered cybersecurity simulation platform that implements a continuous "Cat and Mouse" game between offensive (Red) and defensive (Blue) AI agents with adaptive learning and human feedback integration.

## Features

- **Red Agent**: Autonomous offensive security testing with reconnaissance, scanning, and exploitation capabilities
- **Blue Agent**: Real-time defensive operations with detection, response, and recovery capabilities
- **Simultaneous Execution**: Both agents run in parallel with real-time coordination
- **RAG Pipeline**: Adaptive learning using ChromaDB vector store and embeddings
- **Multi-LLM Support**: OpenAI, Anthropic, Groq, DeepSeek, and local Ollama models
- **Human Feedback**: Rate agent interactions and provide corrections
- **Fine-Tuning Export**: Export high-quality interactions for model fine-tuning
- **Web Dashboard**: Real-time monitoring of both agents

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    WEB UI (React)                        │
├─────────────────────────────────────────────────────────┤
│                   FASTAPI BACKEND                        │
│         REST API + WebSocket + Sessions                  │
├─────────────────────────────────────────────────────────┤
│              PURPLE ORCHESTRATOR                         │
│         Coordinates Red ⟷ Blue Agents                   │
├────────────────────┬────────────────────────────────────┤
│    RED AGENT       │         BLUE AGENT                  │
│  (Offensive)       │        (Defensive)                  │
│  - nmap            │        - firewall_manager           │
│  - nikto           │        - log_monitor               │
│  - sqlmap          │        - process_watcher           │
│  - gobuster        │        - file_integrity            │
├────────────────────┴────────────────────────────────────┤
│                 CORE SERVICES                            │
│   LLM Engine │ RAG Pipeline │ Tool Runner               │
│   ChromaDB   │ Embeddings   │ Feedback Store            │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/yourname/purple-team-gpt
cd purple-team-gpt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Access
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Manual Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows

# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
purple-team run
# or
uvicorn purple_team_gpt.backend.main:app --reload
```

## Configuration

Edit `.env` file:

```env
# LLM Providers (at least one required)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
GROQ_API_KEY=your-groq-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# Local LLM (optional)
OLLAMA_BASE_URL=http://localhost:11434

# Default Provider
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4o

# ChromaDB
CHROMA_PERSIST_DIR=./data/chromadb
```

## API Endpoints

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions/` | Create new session |
| GET | `/api/v1/sessions/` | List all sessions |
| GET | `/api/v1/sessions/{id}` | Get session details |
| POST | `/api/v1/sessions/{id}/start` | Start simulation |
| POST | `/api/v1/sessions/{id}/stop` | Stop simulation |
| GET | `/api/v1/sessions/{id}/metrics` | Get metrics |

### Feedback

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/feedback/` | Submit feedback |
| GET | `/api/v1/feedback/` | List feedback |
| POST | `/api/v1/feedback/export` | Export for fine-tuning |

### WebSocket

Connect to `/ws/session/{session_id}` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session/SESSION_ID');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle: step, finding, status events
};
```

## Tool Arsenal

### Red Arsenal (Offensive)

| Tool | Description | Risk |
|------|-------------|------|
| nmap | Network/port scanning | Low |
| nikto | Web vulnerability scanning | Low |
| gobuster | Directory brute forcing | Medium |
| sqlmap | SQL injection testing | High |
| hydra | Credential brute forcing | High |

### Blue Arsenal (Defensive)

| Tool | Description | Risk |
|------|-------------|------|
| firewall_manager | iptables/ufw management | Medium |
| log_monitor | Log analysis & detection | Low |
| process_watcher | Process monitoring | Low |
| file_integrity | FIM for critical files | Low |

## Project Structure

```
purple-team-gpt/
├── src/purple_team_gpt/
│   ├── agents/          # Red and Blue agents
│   ├── backend/         # FastAPI application
│   ├── core/            # LLM, RAG, Orchestrator
│   ├── feedback/        # Human feedback system
│   └── tools/           # Tool execution
├── scripts/
│   ├── red_arsenal/     # Offensive tools
│   └── blue_arsenal/    # Defensive tools
├── src/frontend/        # React web UI
├── tests/               # Test suite
├── config/              # Configuration files
├── docs/                # Documentation
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/purple_team_gpt --cov-report=html
```

## Security Considerations

1. **Authorization Required**: Only test targets you have explicit permission to test
2. **Safe Mode**: Default mode prevents destructive operations
3. **Tool Sandboxing**: Tools run in isolated Docker containers
4. **Audit Logging**: All actions are logged for compliance
5. **API Key Security**: Never commit API keys to version control

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Submit a pull request

## License

MIT License - See LICENSE file for details.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Detailed system design
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Development roadmap

## Credits

Inspired by [HackBot](https://github.com/yashab-cyber/hackbot) - AI cybersecurity assistant.

---

**Warning**: This tool is for authorized security testing only. Unauthorized use is illegal and unethical.