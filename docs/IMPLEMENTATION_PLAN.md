# Purple Team GPT Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a production-ready Purple Team GPT - autonomous cybersecurity simulation framework with Red/Blue agents, RAG-based learning, and web UI.

**Architecture:** Multi-agent LLM system with FastAPI backend, React frontend, ChromaDB for vector storage, and Docker containerization.

**Tech Stack:** Python 3.11, FastAPI, React, TypeScript, ChromaDB, LiteLLM, Docker

---

## Phase 1: Project Foundation

### Task 1.1: Initialize Project Structure

**Objective:** Set up complete project directory structure with all necessary files.

**Files:**
- Create: `purple-team-gpt/pyproject.toml`
- Create: `purple-team-gpt/requirements.txt`
- Create: `purple-team-gpt/.env.example`
- Create: `purple-team-gpt/.gitignore`
- Create: `purple-team-gpt/README.md`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "purple-team-gpt"
version = "0.1.0"
description = "Autonomous Purple Team cybersecurity simulation framework"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "websockets>=12.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "litellm>=1.20.0",
    "chromadb>=0.4.22",
    "sentence-transformers>=2.2.0",
    "sqlmodel>=0.0.14",
    "aiosqlite>=0.19.0",
    "python-multipart>=0.0.6",
    "python-dotenv>=1.0.0",
    "httpx>=0.26.0",
    "aiohttp>=3.9.0",
    "rich>=13.7.0",
    "typer>=0.9.0",
    "paramiko>=3.4.0",
    "fabric>=3.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.8.0",
    "ruff>=0.1.0",
    "black>=24.1.0",
]

[project.scripts]
purple-team = "purple_team_gpt.cli:main"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ["py311"]
```

**Step 2: Create requirements.txt**

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
websockets>=12.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
litellm>=1.20.0
chromadb>=0.4.22
sentence-transformers>=2.2.0
sqlmodel>=0.0.14
aiosqlite>=0.19.0
python-multipart>=0.0.6
python-dotenv>=1.0.0
httpx>=0.26.0
aiohttp>=3.9.0
rich>=13.7.0
typer>=0.9.0
paramiko>=3.4.0
fabric>=3.2.0
```

**Step 3: Create .env.example**

```env
# LLM API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
GROQ_API_KEY=your-groq-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# Local LLM (Ollama)
OLLAMA_BASE_URL=http://localhost:11434

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_PERSIST_DIR=./data/chromadb

# Application
DEBUG=true
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-for-sessions

# Default Provider
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
```

**Step 4: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
.Python
build/
dist/
*.egg-info/
.eggs/

# Environment
.env
.venv/
venv/
env/

# IDE
.idea/
.vscode/
*.swp

# Data
data/
*.db
*.sqlite

# Logs
*.log
logs/

# Node
node_modules/

# Build
dist/
build/

# ChromaDB
chroma.sqlite3
```

**Step 5: Create README.md**

```markdown
# Purple Team GPT

Autonomous Purple Team cybersecurity simulation framework.

## Features

- **Red Agent**: Offensive security testing
- **Blue Agent**: Defensive security operations  
- **RAG Pipeline**: Adaptive learning from interactions
- **Multi-LLM**: Support for OpenAI, Anthropic, Groq, Ollama
- **Web UI**: Real-time dashboard for monitoring

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourname/purple-team-gpt
cd purple-team-gpt
cp .env.example .env
# Edit .env with your API keys

# Docker
docker-compose up -d

# Or manual
pip install -e .
purple-team
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
```

**Verification:** Run `ls -la purple-team-gpt/` to confirm files exist.

---

### Task 1.2: Create Configuration System

**Objective:** Implement settings management with environment variable support.

**Files:**
- Create: `src/purple_team_gpt/__init__.py`
- Create: `src/purple_team_gpt/config.py`

**Step 1: Create __init__.py**

```python
"""
Purple Team GPT - Autonomous Cybersecurity Simulation Framework
"""

__version__ = "0.1.0"
__app_name__ = "Purple Team GPT"
```

**Step 2: Create config.py**

```python
"""Configuration management using pydantic-settings."""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider configuration."""
    
    model_config = SettingsConfigDict(env_prefix="LLM_")
    
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    
    default_provider: Literal["openai", "anthropic", "groq", "ollama", "deepseek"] = "openai"
    default_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096


class ChromaSettings(BaseSettings):
    """ChromaDB configuration."""
    
    model_config = SettingsConfigDict(env_prefix="CHROMA_")
    
    host: str = "localhost"
    port: int = 8001
    persist_dir: str = "./data/chromadb"


class AppSettings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(env_prefix="APP_")
    
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    host: str = "0.0.0.0"
    port: int = 8000


class AgentSettings(BaseSettings):
    """Agent configuration."""
    
    model_config = SettingsConfigDict(env_prefix="AGENT_")
    
    max_steps: int = 50
    timeout: int = 300
    safe_mode: bool = True
    auto_confirm: bool = False


class Settings(BaseSettings):
    """Main settings container."""
    
    llm: LLMSettings = Field(default_factory=LLMSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

**Verification:** Run `python -c "from src.purple_team_gpt.config import get_settings; print(get_settings())"`

---

## Phase 2: Core LLM Engine

### Task 2.1: Implement Multi-Provider LLM Engine

**Objective:** Create LLM engine with LiteLLM for multi-provider support.

**Files:**
- Create: `src/purple_team_gpt/core/__init__.py`
- Create: `src/purple_team_gpt/core/llm/__init__.py`
- Create: `src/purple_team_gpt/core/llm/engine.py`
- Create: `src/purple_team_gpt/core/llm/providers.py`

**Step 1: Create engine.py**

```python
"""Multi-provider LLM engine with LiteLLM."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import litellm
from litellm import acompletion

from purple_team_gpt.config import LLMSettings

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.drop_params = True


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"


@dataclass
class Message:
    """Chat message."""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Conversation container."""
    messages: List[Message] = field(default_factory=list)
    system_prompt: str = ""
    
    def add(self, role: str, content: str, **metadata) -> Message:
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        return msg
    
    def to_api_format(self) -> List[Dict[str, str]]:
        result = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result
    
    def clear(self) -> None:
        self.messages.clear()


class LLMEngine:
    """Multi-provider LLM engine with automatic failover."""
    
    PROVIDER_MODELS = {
        Provider.OPENAI: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o3-mini"],
        Provider.ANTHROPIC: ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-haiku-20241022"],
        Provider.GROQ: ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        Provider.OLLAMA: ["llama3.2", "mistral", "codellama"],
        Provider.DEEPSEEK: ["deepseek-chat", "deepseek-reasoner"],
    }
    
    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self._setup_api_keys()
        self._failover_order = self._get_failover_order()
    
    def _setup_api_keys(self) -> None:
        """Set API keys from settings."""
        if self.settings.openai_api_key:
            litellm.api_key = self.settings.openai_api_key
        # LiteLLM handles other providers via model prefix
    
    def _get_failover_order(self) -> List[Provider]:
        """Get provider failover order based on available keys."""
        order = []
        if self.settings.openai_api_key:
            order.append(Provider.OPENAI)
        if self.settings.anthropic_api_key:
            order.append(Provider.ANTHROPIC)
        if self.settings.groq_api_key:
            order.append(Provider.GROQ)
        if self.settings.deepseek_api_key:
            order.append(Provider.DEEPSEEK)
        order.append(Provider.OLLAMA)  # Always available locally
        return order
    
    def _get_model_string(self, provider: Provider, model: str) -> str:
        """Convert to LiteLLM model string format."""
        prefix_map = {
            Provider.OPENAI: "openai/",
            Provider.ANTHROPIC: "anthropic/",
            Provider.GROQ: "groq/",
            Provider.OLLAMA: "ollama/",
            Provider.DEEPSEEK: "deepseek/",
        }
        return f"{prefix_map[provider]}{model}"
    
    async def chat(
        self,
        conversation: Conversation,
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Send conversation to LLM and return response."""
        messages = conversation.to_api_format()
        
        for provider in self._failover_order:
            try:
                model = self._get_model_string(provider, self.settings.default_model)
                
                if stream and on_token:
                    return await self._stream_chat(model, messages, on_token)
                else:
                    return await self._blocking_chat(model, messages)
                    
            except Exception as e:
                logger.warning(f"Provider {provider} failed: {e}")
                continue
        
        raise RuntimeError("All LLM providers failed")
    
    async def _blocking_chat(self, model: str, messages: List[Dict]) -> str:
        """Non-streaming chat completion."""
        response = await acompletion(
            model=model,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )
        return response.choices[0].message.content or ""
    
    async def _stream_chat(
        self,
        model: str,
        messages: List[Dict],
        on_token: Callable[[str], None],
    ) -> str:
        """Streaming chat completion."""
        response = await acompletion(
            model=model,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            stream=True,
        )
        
        full_response = []
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response.append(token)
                on_token(token)
        
        return "".join(full_response)
    
    async def quick_ask(
        self,
        prompt: str,
        system: str = "",
    ) -> str:
        """One-shot question without conversation history."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        model = self._get_model_string(self._failover_order[0], self.settings.default_model)
        return await self._blocking_chat(model, messages)
    
    def is_configured(self) -> bool:
        """Check if at least one provider is configured."""
        return bool(self.settings.openai_api_key or 
                   self.settings.anthropic_api_key or
                   self.settings.groq_api_key)
```

**Verification:** Run unit test for LLM engine initialization.

---

## Phase 3: RAG Pipeline

### Task 3.1: Implement Embedding Engine

**Objective:** Create embedding engine for vector generation.

**Files:**
- Create: `src/purple_team_gpt/core/rag/__init__.py`
- Create: `src/purple_team_gpt/core/rag/embeddings.py`

**Step 1: Create embeddings.py**

```python
"""Embedding engine using sentence-transformers or OpenAI."""

import logging
from typing import List, Optional

from purple_team_gpt.config import LLMSettings

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Generate embeddings for text using local or cloud models."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        use_openai: bool = False,
        openai_api_key: Optional[str] = None,
    ):
        self.model_name = model_name
        self.use_openai = use_openai
        self.openai_api_key = openai_api_key
        self._model = None
        
        if not use_openai:
            self._load_local_model()
    
    def _load_local_model(self) -> None:
        """Load sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed, using mock embeddings")
            self._model = None
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for list of texts."""
        if self.use_openai and self.openai_api_key:
            return await self._embed_openai(texts)
        elif self._model:
            return self._embed_local(texts)
        else:
            return self._embed_mock(texts)
    
    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model."""
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in response.data]
    
    def _embed_mock(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for testing."""
        import hashlib
        import struct
        
        embeddings = []
        for text in texts:
            # Generate deterministic pseudo-embedding from hash
            h = hashlib.sha256(text.encode()).digest()
            embedding = list(struct.unpack(f'{32}f', h))
            # Normalize
            norm = sum(x**2 for x in embedding) ** 0.5
            embeddings.append([x/norm for x in embedding])
        return embeddings
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        if self.use_openai:
            return 1536
        elif self._model:
            return self._model.get_sentence_embedding_dimension()
        return 128  # Mock dimension
```

---

### Task 3.2: Implement ChromaDB Vector Store

**Objective:** Create vector store for RAG using ChromaDB.

**Files:**
- Create: `src/purple_team_gpt/core/rag/vector_store.py`

```python
"""ChromaDB vector store for RAG."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from purple_team_gpt.config import ChromaSettings as AppChromaSettings
from purple_team_gpt.core.rag.embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-based vector store for RAG."""
    
    COLLECTIONS = ["attack_patterns", "defense_patterns", "feedback_store", "session_logs"]
    
    def __init__(
        self,
        settings: AppChromaSettings,
        embedding_engine: EmbeddingEngine,
    ):
        self.settings = settings
        self.embedding_engine = embedding_engine
        self._client = None
        self._collections: Dict[str, chromadb.Collection] = {}
    
    def _get_client(self) -> chromadb.ClientAPI:
        """Get or create ChromaDB client."""
        if self._client is None:
            if self.settings.host == "localhost" and self.settings.persist_dir:
                # Local persistent client
                self._client = chromadb.PersistentClient(
                    path=self.settings.persist_dir,
                )
            else:
                # Remote client
                self._client = chromadb.HttpClient(
                    host=self.settings.host,
                    port=self.settings.port,
                )
        return self._client
    
    def get_collection(self, name: str) -> chromadb.Collection:
        """Get or create a collection."""
        if name not in self._collections:
            client = self._get_client()
            self._collections[name] = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]
    
    async def add(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """Add documents to collection."""
        collection = self.get_collection(collection_name)
        
        # Generate embeddings
        embeddings = await self.embedding_engine.embed(documents)
        
        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Add timestamp to metadata
        if metadatas is None:
            metadatas = [{} for _ in documents]
        for meta in metadatas:
            meta["timestamp"] = datetime.utcnow().isoformat()
        
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        
        logger.debug(f"Added {len(documents)} documents to {collection_name}")
    
    async def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query collection for similar documents."""
        collection = self.get_collection(collection_name)
        
        # Generate query embedding
        query_embedding = (await self.embedding_engine.embed([query_text]))[0]
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        
        return {
            "ids": results["ids"][0],
            "documents": results["documents"][0],
            "metadatas": results["metadatas"][0],
            "distances": results["distances"][0],
        }
    
    async def get_context(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        n_results_per_collection: int = 3,
    ) -> str:
        """Get aggregated context from multiple collections for RAG."""
        if collections is None:
            collections = self.COLLECTIONS
        
        contexts = []
        for collection_name in collections:
            try:
                results = await self.query(
                    collection_name,
                    query,
                    n_results=n_results_per_collection,
                )
                for doc, meta, dist in zip(
                    results["documents"],
                    results["metadatas"],
                    results["distances"],
                ):
                    if dist < 0.5:  # Similarity threshold
                        contexts.append(f"[{collection_name}] {doc}")
            except Exception as e:
                logger.debug(f"Query {collection_name} failed: {e}")
        
        return "\n\n".join(contexts) if contexts else ""
    
    def count(self, collection_name: str) -> int:
        """Get document count in collection."""
        return self.get_collection(collection_name).count()
```

---

## Phase 4: Agent System

### Task 4.1: Create Base Agent Class

**Objective:** Implement base agent class with common functionality.

**Files:**
- Create: `src/purple_team_gpt/agents/__init__.py`
- Create: `src/purple_team_gpt/agents/base.py`

```python
"""Base agent class."""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from purple_team_gpt.core.llm.engine import Conversation, LLMEngine
from purple_team_gpt.core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    RED = "red"
    BLUE = "blue"
    PURPLE = "purple"


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentAction:
    """Represents an agent action."""
    action_type: str  # "execute", "report", "query_rag", "wait"
    tool: Optional[str] = None
    command: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentStep:
    """A single step in agent execution."""
    step_num: int
    action: AgentAction
    result: Optional[str] = None
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Finding:
    """A security finding."""
    title: str
    severity: str  # Critical, High, Medium, Low, Info
    description: str
    evidence: str = ""
    recommendation: str = ""
    tool: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseAgent(ABC):
    """Base class for all agents."""
    
    role: AgentRole = AgentRole.PURPLE
    
    def __init__(
        self,
        engine: LLMEngine,
        vector_store: VectorStore,
        on_step: Optional[Callable[[AgentStep], None]] = None,
        on_finding: Optional[Callable[[Finding], None]] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ):
        self.engine = engine
        self.vector_store = vector_store
        self.on_step = on_step
        self.on_finding = on_finding
        self.on_output = on_output
        
        self.conversation = Conversation()
        self.state = AgentState.IDLE
        self.steps: List[AgentStep] = []
        self.findings: List[Finding] = []
        self.target = ""
        self.scope = ""
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    async def plan(self, context: str) -> List[AgentAction]:
        """Plan next actions based on context."""
        pass
    
    @abstractmethod
    async def execute_action(self, action: AgentAction) -> str:
        """Execute a single action."""
        pass
    
    def initialize(self, target: str, scope: str = "") -> None:
        """Initialize agent for a new session."""
        self.target = target
        self.scope = scope
        self.conversation = Conversation()
        self.conversation.system_prompt = self.system_prompt
        self.steps = []
        self.findings = []
        self.state = AgentState.IDLE
    
    async def query_rag(self, query: str) -> str:
        """Query vector store for relevant context."""
        return await self.vector_store.get_context(query)
    
    def _parse_actions(self, response: str) -> List[AgentAction]:
        """Parse JSON action blocks from LLM response."""
        actions = []
        
        # Find JSON blocks
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                action = AgentAction(
                    action_type=data.get("action", "unknown"),
                    tool=data.get("tool"),
                    command=data.get("command"),
                    parameters=data.get("parameters", {}),
                    explanation=data.get("explanation", ""),
                )
                actions.append(action)
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse action: {match[:100]}")
        
        return actions
    
    def add_finding(self, finding: Finding) -> None:
        """Add a finding and notify callback."""
        self.findings.append(finding)
        if self.on_finding:
            self.on_finding(finding)
    
    def add_step(self, step: AgentStep) -> None:
        """Add a step and notify callback."""
        self.steps.append(step)
        if self.on_step:
            self.on_step(step)
    
    def output(self, message: str) -> None:
        """Send output to callback."""
        if self.on_output:
            self.on_output(message)
    
    async def store_interaction(self, content: str, metadata: Dict[str, Any]) -> None:
        """Store interaction in vector store for learning."""
        collection = f"{self.role.value}_patterns"
        await self.vector_store.add(
            collection_name=collection,
            documents=[content],
            metadatas=[metadata],
        )
```

---

### Task 4.2: Implement Red Agent

**Objective:** Create offensive security agent.

**Files:**
- Create: `src/purple_team_gpt/agents/red_agent.py`

```python
"""Red Agent - Offensive security testing."""

import logging
from typing import Dict, List, Optional

from purple_team_gpt.agents.base import AgentAction, AgentRole, AgentState, BaseAgent, Finding

logger = logging.getLogger(__name__)


RED_AGENT_PROMPT = """You are the Red Agent, an autonomous offensive security testing AI.

IDENTITY:
You are part of Purple Team GPT, a cybersecurity simulation framework.
Your role is to perform authorized offensive security testing.

CAPABILITIES:
- Reconnaissance: Port scanning, service enumeration, OS fingerprinting
- Vulnerability scanning: Web app scanning, CVE detection
- Exploitation: SQL injection testing, credential testing
- Post-exploitation: Privilege escalation checks

AVAILABLE TOOLS:
- nmap: Network/port scanning
- nikto: Web vulnerability scanning  
- gobuster: Directory brute forcing
- sqlmap: SQL injection testing
- hydra: Credential brute forcing

RULES:
1. Only test targets you have explicit authorization for
2. Follow methodology: Recon → Scan → Enumerate → Test → Report
3. Document all findings with severity ratings
4. Use safe_mode to avoid destructive operations
5. Learn from past successes stored in RAG memory

OUTPUT FORMAT:
To execute a tool, include a JSON action block:
```json
{
  "action": "execute",
  "tool": "nmap",
  "command": "nmap -sV -sC target",
  "explanation": "Service version detection with default scripts"
}
```

To report a finding:
```json
{
  "action": "finding",
  "title": "Open SSH Port",
  "severity": "Medium",
  "description": "SSH service exposed on port 22",
  "evidence": "22/tcp open ssh",
  "recommendation": "Restrict SSH access via firewall"
}
```

When assessment is complete:
```json
{"action": "complete", "summary": "Assessment finished"}
```
"""


class RedAgent(BaseAgent):
    """Offensive security testing agent."""
    
    role = AgentRole.RED
    
    @property
    def system_prompt(self) -> str:
        return RED_AGENT_PROMPT
    
    async def plan(self, context: str) -> List[AgentAction]:
        """Plan offensive actions based on context."""
        # Query RAG for similar attack patterns
        rag_context = await self.query_rag(f"attack patterns for {self.target}")
        
        # Build planning prompt
        planning_prompt = f"""Target: {self.target}
Scope: {self.scope or 'Full authorized assessment'}

Context from previous engagements:
{rag_context}

Current situation:
{context}

Plan your next actions. Consider:
1. What reconnaissance is needed?
2. What services/ports should be scanned?
3. What vulnerabilities might exist?
4. What tools would be most effective?

Provide your plan as JSON action blocks."""

        self.conversation.add("user", planning_prompt)
        response = await self.engine.chat(self.conversation)
        self.conversation.add("assistant", response)
        
        return self._parse_actions(response)
    
    async def execute_action(self, action: AgentAction) -> str:
        """Execute an offensive action."""
        if action.action_type == "execute":
            return await self._execute_tool(action)
        elif action.action_type == "finding":
            return await self._record_finding(action)
        elif action.action_type == "complete":
            self.state = AgentState.COMPLETED
            return "Assessment completed"
        else:
            return f"Unknown action type: {action.action_type}"
    
    async def _execute_tool(self, action: AgentAction) -> str:
        """Execute a security tool."""
        # Import tool runner
        from purple_team_gpt.tools.runner import ToolRunner
        
        runner = ToolRunner()
        result = await runner.execute(
            command=action.command or "",
            tool_name=action.tool or "unknown",
            timeout=300,
        )
        
        # Store result for learning
        await self.store_interaction(
            content=f"Tool: {action.tool}\nCommand: {action.command}\nResult: {result.output[:500]}",
            metadata={
                "tool": action.tool,
                "target": self.target,
                "success": result.success,
            }
        )
        
        return result.output
    
    async def _record_finding(self, action: AgentAction) -> str:
        """Record a security finding."""
        finding = Finding(
            title=action.parameters.get("title", "Unknown"),
            severity=action.parameters.get("severity", "Info"),
            description=action.parameters.get("description", ""),
            evidence=action.parameters.get("evidence", ""),
            recommendation=action.parameters.get("recommendation", ""),
            tool=action.tool or "",
        )
        self.add_finding(finding)
        
        # Store in RAG
        await self.store_interaction(
            content=f"Finding: {finding.title}\nSeverity: {finding.severity}\n{finding.description}",
            metadata={
                "type": "finding",
                "severity": finding.severity,
                "target": self.target,
            }
        )
        
        return f"Recorded finding: {finding.title}"
    
    async def run_step(self, context: str = "") -> str:
        """Execute a single step of the assessment."""
        self.state = AgentState.RUNNING
        
        actions = await self.plan(context)
        
        results = []
        for action in actions:
            result = await self.execute_action(action)
            results.append(result)
            
            if self.state == AgentState.COMPLETED:
                break
        
        return "\n\n".join(results)
```

---

### Task 4.3: Implement Blue Agent

**Objective:** Create defensive security agent.

**Files:**
- Create: `src/purple_team_gpt/agents/blue_agent.py`

```python
"""Blue Agent - Defensive security operations."""

import logging
from typing import Dict, List, Optional

from purple_team_gpt.agents.base import AgentAction, AgentRole, AgentState, BaseAgent, Finding

logger = logging.getLogger(__name__)


BLUE_AGENT_PROMPT = """You are the Blue Agent, an autonomous defensive security AI.

IDENTITY:
You are part of Purple Team GPT, a cybersecurity simulation framework.
Your role is to detect and respond to security threats in real-time.

CAPABILITIES:
- Detection: Log analysis, anomaly detection, threat identification
- Response: Firewall rules, service management, incident containment
- Recovery: Rollback procedures, patch recommendations
- Hardening: Security configurations, best practices

AVAILABLE TOOLS:
- log_monitor: Real-time log analysis
- firewall_manager: iptables rule management
- process_watcher: Monitor running processes
- file_integrity: File integrity monitoring
- service_manager: Start/stop/restart services

RULES:
1. Monitor for suspicious activity continuously
2. Respond proportionally to threat severity
3. Document all defensive actions
4. Learn from past successful defenses
5. Coordinate with Red Agent findings

OUTPUT FORMAT:
To execute a defense action:
```json
{
  "action": "execute",
  "tool": "firewall_manager",
  "command": "block_ip 192.168.1.100",
  "explanation": "Blocking suspicious IP detected in logs"
}
```

To report a detection:
```json
{
  "action": "detection",
  "title": "Brute Force Attempt",
  "severity": "High",
  "description": "Multiple failed SSH login attempts",
  "evidence": "100+ failed auth attempts from IP",
  "response": "IP blocked, alert generated"
}
```

When defense session is complete:
```json
{"action": "complete", "summary": "Defense session ended"}
```
"""


class BlueAgent(BaseAgent):
    """Defensive security agent."""
    
    role = AgentRole.BLUE
    
    @property
    def system_prompt(self) -> str:
        return BLUE_AGENT_PROMPT
    
    async def plan(self, context: str) -> List[AgentAction]:
        """Plan defensive actions based on context."""
        # Query RAG for similar threat patterns
        rag_context = await self.query_rag(f"defense patterns for {context[:100]}")
        
        # Build planning prompt
        planning_prompt = f"""Current system state:
{context}

Previous defense knowledge:
{rag_context}

Analyze the situation and plan defensive actions. Consider:
1. What threats are present?
2. What is the severity level?
3. What immediate responses are needed?
4. What long-term hardening is recommended?

Provide your plan as JSON action blocks."""

        self.conversation.add("user", planning_prompt)
        response = await self.engine.chat(self.conversation)
        self.conversation.add("assistant", response)
        
        return self._parse_actions(response)
    
    async def execute_action(self, action: AgentAction) -> str:
        """Execute a defensive action."""
        if action.action_type == "execute":
            return await self._execute_tool(action)
        elif action.action_type == "detection":
            return await self._record_detection(action)
        elif action.action_type == "complete":
            self.state = AgentState.COMPLETED
            return "Defense session completed"
        else:
            return f"Unknown action type: {action.action_type}"
    
    async def _execute_tool(self, action: AgentAction) -> str:
        """Execute a defense tool."""
        from purple_team_gpt.tools.runner import ToolRunner
        
        runner = ToolRunner()
        result = await runner.execute(
            command=action.command or "",
            tool_name=action.tool or "unknown",
            timeout=60,
        )
        
        # Store result for learning
        await self.store_interaction(
            content=f"Defense: {action.tool}\nAction: {action.command}\nResult: {result.output[:500]}",
            metadata={
                "tool": action.tool,
                "success": result.success,
                "type": "defense",
            }
        )
        
        return result.output
    
    async def _record_detection(self, action: AgentAction) -> str:
        """Record a threat detection."""
        finding = Finding(
            title=action.parameters.get("title", "Unknown Detection"),
            severity=action.parameters.get("severity", "Info"),
            description=action.parameters.get("description", ""),
            evidence=action.parameters.get("evidence", ""),
            recommendation=action.parameters.get("response", ""),
            tool=action.tool or "detection",
        )
        self.add_finding(finding)
        
        # Store in RAG
        await self.store_interaction(
            content=f"Detection: {finding.title}\nSeverity: {finding.severity}\n{finding.description}",
            metadata={
                "type": "detection",
                "severity": finding.severity,
            }
        )
        
        return f"Recorded detection: {finding.title}"
    
    async def monitor(self, log_data: str) -> List[AgentAction]:
        """Analyze logs and detect threats."""
        analysis_prompt = f"""Analyze the following log data for security threats:

```
{log_data[:2000]}
```

Identify:
1. Suspicious patterns
2. Potential attacks
3. Anomalous behavior
4. Recommended responses

Provide findings as JSON action blocks."""

        self.conversation.add("user", analysis_prompt)
        response = await self.engine.chat(self.conversation)
        self.conversation.add("assistant", response)
        
        return self._parse_actions(response)
    
    async def respond_to_event(self, event: Dict) -> str:
        """Respond to an event from the Red Agent."""
        event_context = f"""Red Agent Event Received:
Type: {event.get('type', 'unknown')}
Data: {event.get('data', {})}

Plan and execute defensive response."""

        actions = await self.plan(event_context)
        
        results = []
        for action in actions:
            result = await self.execute_action(action)
            results.append(result)
        
        return "\n\n".join(results)
```

---

## Phase 5: Agent Coordination

### Task 5.1: Implement Purple Orchestrator

**Objective:** Create coordination layer for simultaneous agent execution.

**Files:**
- Create: `src/purple_team_gpt/core/orchestrator.py`

```python
"""Purple Orchestrator - Coordinates Red and Blue agents."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import uuid

from purple_team_gpt.agents.base import AgentState, Finding
from purple_team_gpt.agents.red_agent import RedAgent
from purple_team_gpt.agents.blue_agent import BlueAgent
from purple_team_gpt.core.llm.engine import LLMEngine
from purple_team_gpt.core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Session:
    """A simulation session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: str = ""
    scope: str = ""
    status: SessionStatus = SessionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    red_findings: List[Finding] = field(default_factory=list)
    blue_findings: List[Finding] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentEvent:
    """Event from an agent."""
    session_id: str
    agent: str  # "red" or "blue"
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PurpleOrchestrator:
    """Coordinates Red and Blue agents in real-time."""
    
    def __init__(
        self,
        engine: LLMEngine,
        vector_store: VectorStore,
        on_event: Optional[Callable[[AgentEvent], None]] = None,
    ):
        self.engine = engine
        self.vector_store = vector_store
        self.on_event = on_event
        
        self.sessions: Dict[str, Session] = {}
        self.red_agents: Dict[str, RedAgent] = {}
        self.blue_agents: Dict[str, BlueAgent] = {}
        self._event_queues: Dict[str, asyncio.Queue] = {}
    
    def create_session(self, target: str, scope: str = "") -> Session:
        """Create a new simulation session."""
        session = Session(target=target, scope=scope)
        self.sessions[session.id] = session
        self._event_queues[session.id] = asyncio.Queue()
        
        # Create agents
        self.red_agents[session.id] = RedAgent(
            engine=self.engine,
            vector_store=self.vector_store,
            on_step=lambda s: self._handle_step(session.id, "red", s),
            on_finding=lambda f: self._handle_finding(session.id, "red", f),
        )
        
        self.blue_agents[session.id] = BlueAgent(
            engine=self.engine,
            vector_store=self.vector_store,
            on_step=lambda s: self._handle_step(session.id, "blue", s),
            on_finding=lambda f: self._handle_finding(session.id, "blue", f),
        )
        
        logger.info(f"Created session {session.id} for target {target}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    async def start_session(self, session_id: str) -> None:
        """Start the simulation with both agents."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.status = SessionStatus.RUNNING
        
        # Initialize agents
        red_agent = self.red_agents[session_id]
        blue_agent = self.blue_agents[session_id]
        
        red_agent.initialize(session.target, session.scope)
        blue_agent.initialize(session.target, session.scope)
        
        # Run both agents simultaneously
        await asyncio.gather(
            self._run_red_agent(session_id),
            self._run_blue_agent(session_id),
        )
        
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()
    
    async def _run_red_agent(self, session_id: str) -> None:
        """Run red agent loop."""
        red_agent = self.red_agents[session_id]
        session = self.sessions[session_id]
        
        # Initial reconnaissance
        context = f"Starting assessment of {session.target}"
        
        while red_agent.state != AgentState.COMPLETED:
            if session.status == SessionStatus.PAUSED:
                await asyncio.sleep(1)
                continue
            
            try:
                result = await red_agent.run_step(context)
                
                # Emit event to Blue agent
                await self._emit_event(session_id, "red", "step_complete", {
                    "result": result[:500],
                    "findings": len(red_agent.findings),
                })
                
                # Update context
                context = result
                
                # Small delay between steps
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Red agent error: {e}")
                await self._emit_event(session_id, "red", "error", {"error": str(e)})
                break
    
    async def _run_blue_agent(self, session_id: str) -> None:
        """Run blue agent loop."""
        blue_agent = self.blue_agents[session_id]
        session = self.sessions[session_id]
        
        while session.status == SessionStatus.RUNNING:
            try:
                # Wait for events
                event = await self._event_queues[session_id].get()
                
                if event["agent"] == "red":
                    # Process Red agent event
                    response = await blue_agent.respond_to_event(event)
                    
                    await self._emit_event(session_id, "blue", "response", {
                        "response": response[:500],
                    })
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Blue agent error: {e}")
    
    async def _emit_event(
        self,
        session_id: str,
        agent: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Emit an event to the event queue and callback."""
        event = AgentEvent(
            session_id=session_id,
            agent=agent,
            event_type=event_type,
            data=data,
        )
        
        # Add to queue
        if session_id in self._event_queues:
            await self._event_queues[session_id].put({
                "agent": agent,
                "event_type": event_type,
                "data": data,
            })
        
        # Call callback
        if self.on_event:
            self.on_event(event)
        
        # Store in session
        session = self.sessions.get(session_id)
        if session:
            session.events.append({
                "agent": agent,
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            })
    
    def _handle_step(self, session_id: str, agent: str, step) -> None:
        """Handle agent step callback."""
        asyncio.create_task(self._emit_event(session_id, agent, "step", {
            "step_num": step.step_num,
            "action": step.action.action_type,
            "success": step.success,
        }))
    
    def _handle_finding(self, session_id: str, agent: str, finding: Finding) -> None:
        """Handle agent finding callback."""
        session = self.sessions.get(session_id)
        if session:
            if agent == "red":
                session.red_findings.append(finding)
            else:
                session.blue_findings.append(finding)
        
        asyncio.create_task(self._emit_event(session_id, agent, "finding", {
            "title": finding.title,
            "severity": finding.severity,
        }))
    
    def pause_session(self, session_id: str) -> None:
        """Pause a running session."""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.PAUSED
    
    def resume_session(self, session_id: str) -> None:
        """Resume a paused session."""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.RUNNING
    
    def stop_session(self, session_id: str) -> Session:
        """Stop a session and return final state."""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.COMPLETED
            session.completed_at = datetime.utcnow()
        return session
    
    def get_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get metrics for a session."""
        session = self.sessions.get(session_id)
        if not session:
            return {}
        
        red_agent = self.red_agents.get(session_id)
        blue_agent = self.blue_agents.get(session_id)
        
        return {
            "session_id": session_id,
            "target": session.target,
            "status": session.status.value,
            "duration": str(session.completed_at - session.created_at) if session.completed_at else "ongoing",
            "red_findings": len(session.red_findings),
            "blue_findings": len(session.blue_findings),
            "red_steps": len(red_agent.steps) if red_agent else 0,
            "blue_steps": len(blue_agent.steps) if blue_agent else 0,
            "total_events": len(session.events),
        }
```

---

## Phase 6: FastAPI Backend

### Task 6.1: Create FastAPI Application

**Objective:** Build REST API and WebSocket endpoints.

**Files:**
- Create: `src/purple_team_gpt/backend/__init__.py`
- Create: `src/purple_team_gpt/backend/main.py`
- Create: `src/purple_team_gpt/backend/routers/__init__.py`
- Create: `src/purple_team_gpt/backend/routers/sessions.py`
- Create: `src/purple_team_gpt/backend/routers/websocket.py`

**Step 1: Create main.py**

```python
"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from purple_team_gpt.config import get_settings
from purple_team_gpt.core.llm.engine import LLMEngine
from purple_team_gpt.core.rag.embeddings import EmbeddingEngine
from purple_team_gpt.core.rag.vector_store import VectorStore
from purple_team_gpt.core.orchestrator import PurpleOrchestrator

logger = logging.getLogger(__name__)

# Global instances
llm_engine: LLMEngine = None
vector_store: VectorStore = None
orchestrator: PurpleOrchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global llm_engine, vector_store, orchestrator
    
    settings = get_settings()
    
    # Initialize LLM engine
    llm_engine = LLMEngine(settings.llm)
    logger.info("LLM engine initialized")
    
    # Initialize vector store
    embedding_engine = EmbeddingEngine(
        use_openai=bool(settings.llm.openai_api_key),
        openai_api_key=settings.llm.openai_api_key,
    )
    vector_store = VectorStore(settings.chroma, embedding_engine)
    logger.info("Vector store initialized")
    
    # Initialize orchestrator
    orchestrator = PurpleOrchestrator(llm_engine, vector_store)
    logger.info("Orchestrator initialized")
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")


app = FastAPI(
    title="Purple Team GPT",
    description="Autonomous Purple Team cybersecurity simulation",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Purple Team GPT API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "llm_configured": llm_engine.is_configured() if llm_engine else False,
    }


# Include routers
from purple_team_gpt.backend.routers import sessions, websocket

app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
```

**Step 2: Create sessions.py router**

```python
"""Session management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from purple_team_gpt.backend.main import orchestrator

router = APIRouter()


class SessionCreate(BaseModel):
    target: str
    scope: Optional[str] = ""


class SessionResponse(BaseModel):
    id: str
    target: str
    scope: str
    status: str


@router.post("/", response_model=SessionResponse)
async def create_session(data: SessionCreate):
    """Create a new simulation session."""
    session = orchestrator.create_session(data.target, data.scope)
    return SessionResponse(
        id=session.id,
        target=session.target,
        scope=session.scope,
        status=session.status.value,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        id=session.id,
        target=session.target,
        scope=session.scope,
        status=session.status.value,
    )


@router.post("/{session_id}/start")
async def start_session(session_id: str):
    """Start the simulation."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Start in background
    import asyncio
    asyncio.create_task(orchestrator.start_session(session_id))
    
    return {"message": "Session started", "session_id": session_id}


@router.post("/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop the simulation."""
    session = orchestrator.stop_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session stopped", "session_id": session_id}


@router.get("/{session_id}/metrics")
async def get_metrics(session_id: str):
    """Get session metrics."""
    metrics = orchestrator.get_metrics(session_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Session not found")
    return metrics
```

**Step 3: Create websocket.py router**

```python
"""WebSocket endpoints for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

from purple_team_gpt.backend.main import orchestrator

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
    
    async def broadcast(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    # Set up event handler
    def on_event(event):
        import asyncio
        asyncio.create_task(manager.broadcast(session_id, {
            "agent": event.agent,
            "type": event.event_type,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        }))
    
    # Register callback
    orchestrator.on_event = on_event
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (e.g., feedback)
            message = json.loads(data)
            
            if message.get("type") == "feedback":
                # Store feedback
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
```

---

## Phase 7: Tool Runner

### Task 7.1: Implement Tool Runner

**Objective:** Create safe tool execution environment.

**Files:**
- Create: `src/purple_team_gpt/tools/__init__.py`
- Create: `src/purple_team_gpt/tools/runner.py`

```python
"""Tool execution runner."""

import asyncio
import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    output: str
    error: str = ""
    return_code: int = 0
    duration: float = 0.0


class ToolRunner:
    """Execute security tools safely."""
    
    ALLOWED_TOOLS = {
        "nmap", "nikto", "gobuster", "sqlmap", "hydra",
        "dig", "whois", "curl", "wget", "netcat",
    }
    
    DANGEROUS_FLAGS = {
        "rm", "dd", "mkfs", "format", "shutdown", "reboot",
    }
    
    def __init__(
        self,
        allowed_tools: Optional[List[str]] = None,
        timeout: int = 300,
        safe_mode: bool = True,
    ):
        self.allowed_tools = set(allowed_tools) if allowed_tools else self.ALLOWED_TOOLS
        self.timeout = timeout
        self.safe_mode = safe_mode
    
    def is_tool_available(self, tool: str) -> bool:
        """Check if tool is installed."""
        return shutil.which(tool) is not None
    
    def get_available_tools(self) -> Dict[str, bool]:
        """Get dict of available tools."""
        return {tool: self.is_tool_available(tool) for tool in self.allowed_tools}
    
    def validate_command(self, command: str) -> bool:
        """Validate command for safety."""
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_FLAGS:
            if pattern in command.lower():
                return False
        
        # Check tool is allowed
        tool = command.split()[0] if command.split() else ""
        if tool not in self.allowed_tools:
            return False
        
        return True
    
    async def execute(
        self,
        command: str,
        tool_name: str = "",
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """Execute a command safely."""
        import time
        
        # Validate
        if not self.validate_command(command):
            return ToolResult(
                success=False,
                output="",
                error="Command not allowed - safety validation failed",
                return_code=-1,
            )
        
        start_time = time.time()
        timeout = timeout or self.timeout
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout}s",
                    return_code=-1,
                    duration=time.time() - start_time,
                )
            
            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")
            
            return ToolResult(
                success=process.returncode == 0,
                output=output,
                error=error,
                return_code=process.returncode,
                duration=time.time() - start_time,
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                return_code=-1,
                duration=time.time() - start_time,
            )
```

---

## Phase 8: Docker Configuration

### Task 8.1: Create Docker Files

**Objective:** Set up Docker for cross-platform deployment.

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nmap \
    nikto \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY config/ ./config/

# Create data directory
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "purple_team_gpt.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - DEBUG=true
    depends_on:
      - chromadb
  
  frontend:
    build: ./src/frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
  
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/data

volumes:
  chromadb_data:
```

---

## Verification Checklist

After completing all phases, verify:

- [ ] `python -c "from purple_team_gpt import __version__; print(__version__)"` works
- [ ] `uvicorn purple_team_gpt.backend.main:app --reload` starts server
- [ ] `curl http://localhost:8000/health` returns healthy status
- [ ] Docker compose builds successfully
- [ ] WebSocket connection works
- [ ] RAG queries return results
- [ ] Both agents can execute steps

---

**Plan complete. Ready to execute using subagent-driven-development.**