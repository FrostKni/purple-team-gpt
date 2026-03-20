"""FastAPI application entry point.

This module provides the main FastAPI application with:
- Lifespan context manager for initialization
- CORS middleware for cross-origin requests
- REST API endpoints for session management
- WebSocket support for real-time updates
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from purple_team_gpt import __app_name__, __version__
from purple_team_gpt.config import get_settings
from purple_team_gpt.core.llm.engine import LLMEngine
from purple_team_gpt.core.rag.embeddings import EmbeddingEngine, EmbeddingProvider
from purple_team_gpt.core.rag.vector_store import VectorStore
from purple_team_gpt.core.orchestrator import PurpleOrchestrator
from purple_team_gpt.feedback.store import FeedbackStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances - initialized during lifespan
llm_engine: Optional[LLMEngine] = None
vector_store: Optional[VectorStore] = None
orchestrator: Optional[PurpleOrchestrator] = None
feedback_store: Optional[FeedbackStore] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.
    
    Initializes the LLM engine, vector store, and orchestrator on startup,
    and cleans up resources on shutdown.
    """
    global llm_engine, vector_store, orchestrator, feedback_store
    
    settings = get_settings()
    
    logger.info("Initializing Purple Team GPT backend...")
    
    # Initialize LLM engine with OpenAI-compatible endpoints
    llm_engine = LLMEngine(
        settings=settings.llm,
        openai_compatible_endpoints=settings.openai_compatible_endpoints,
    )
    providers = llm_engine.get_available_providers()
    logger.info(f"LLM engine initialized with providers: {providers}")
    
    # Initialize embedding engine
    embedding_engine = EmbeddingEngine(
        llm_settings=settings.llm,
        provider=EmbeddingProvider.OPENAI if settings.llm.openai_api_key else EmbeddingProvider.LOCAL,
    )
    logger.info(f"Embedding engine initialized: {embedding_engine}")
    
    # Initialize vector store
    vector_store = VectorStore(settings.chroma, embedding_engine)
    vector_store.initialize_collections()
    logger.info("Vector store initialized")
    
    # Initialize orchestrator
    orchestrator = PurpleOrchestrator(
        engine=llm_engine,
        vector_store=vector_store,
        max_steps=settings.agent.max_steps,
        safe_mode=settings.agent.safe_mode,
    )
    logger.info("Orchestrator initialized")
    
    # Initialize feedback store
    feedback_store = FeedbackStore(db_path=f"{settings.chroma.persist_dir}/feedback.db")
    logger.info("Feedback store initialized")
    
    logger.info(f"Purple Team GPT v{__version__} ready")
    
    # Set dependencies on routers
    from purple_team_gpt.backend.routers import sessions, websocket, feedback, llm
    sessions.set_orchestrator(orchestrator)
    websocket.set_dependencies(orchestrator, vector_store)
    feedback.set_feedback_store(feedback_store)
    llm.set_llm_engine(llm_engine)
    
    yield
    
    # Cleanup
    logger.info("Shutting down Purple Team GPT...")


# Create FastAPI application
app = FastAPI(
    title=__app_name__,
    description="Autonomous Purple Team cybersecurity simulation framework",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    """Root endpoint with basic application info."""
    return {
        "name": __app_name__,
        "version": __version__,
        "description": "Autonomous Purple Team cybersecurity simulation",
    }


@app.get("/health")
async def health() -> dict:
    """Health check endpoint.
    
    Returns the health status of the application and its components.
    """
    return {
        "status": "healthy",
        "version": __version__,
        "llm_configured": llm_engine.is_configured() if llm_engine else False,
        "vector_store_ready": vector_store is not None,
        "orchestrator_ready": orchestrator is not None,
        "feedback_store_ready": feedback_store is not None,
    }


@app.get("/status")
async def status() -> dict:
    """Detailed status endpoint.
    
    Returns detailed status information about all components.
    """
    settings = get_settings()
    
    # Get vector store stats
    vector_stats = {}
    if vector_store:
        vector_stats = vector_store.get_stats()
    
    # Get orchestrator metrics
    orchestrator_metrics = {}
    if orchestrator:
        orchestrator_metrics = orchestrator.get_all_metrics()
    
    # Get feedback stats
    feedback_stats = {}
    if feedback_store:
        feedback_stats = feedback_store.get_stats().model_dump()
    
    return {
        "application": {
            "name": __app_name__,
            "version": __version__,
            "debug": settings.app.debug,
        },
        "llm": {
            "configured": llm_engine.is_configured() if llm_engine else False,
            "default_provider": settings.llm.default_provider,
            "default_model": settings.llm.default_model,
            "available_providers": llm_engine.get_available_providers() if llm_engine else [],
            "openai_compatible_endpoints": [
                {"name": ep.name, "base_url": ep.base_url, "model": ep.model, "enabled": ep.enabled}
                for ep in settings.openai_compatible_endpoints
            ],
        },
        "vector_store": {
            "ready": vector_store is not None,
            "stats": vector_stats,
        },
        "orchestrator": {
            "ready": orchestrator is not None,
            "metrics": orchestrator_metrics,
        },
        "feedback": {
            "ready": feedback_store is not None,
            "stats": feedback_stats,
        },
    }


# Include routers
from purple_team_gpt.backend.routers import sessions, websocket, feedback, llm

app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])