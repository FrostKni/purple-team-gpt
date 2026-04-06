"""FastAPI application entry point.

This module provides the main FastAPI application with:
- Lifespan context manager for initialization
- CORS middleware for cross-origin requests (secured)
- JWT authentication for all endpoints
- Rate limiting
- REST API endpoints for session management
- WebSocket support for real-time updates
- PostgreSQL persistence via SQLAlchemy async
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from purple_team_gpt import __app_name__, __version__
from purple_team_gpt.config import get_settings
from purple_team_gpt.core.llm.engine import LLMEngine
from purple_team_gpt.core.rag.embeddings import EmbeddingEngine, EmbeddingProvider
from purple_team_gpt.core.rag.vector_store import VectorStore
from purple_team_gpt.core.orchestrator import PurpleOrchestrator
from purple_team_gpt.feedback.store import FeedbackStore
from purple_team_gpt.backend.security import (
    get_rate_limiter,
    get_current_user,
    rate_limit_dependency,
)
from purple_team_gpt.db.database import init_db, close_db

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
    
    Initializes the LLM engine, vector store, database, and orchestrator on startup,
    and cleans up resources on shutdown.
    """
    global llm_engine, vector_store, orchestrator, feedback_store
    
    settings = get_settings()
    
    logger.info("Initializing Purple Team GPT backend...")
    
    # Initialize database (optional - will continue without if unavailable)
    db_initialized = False
    try:
        await init_db()
        db_initialized = True
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.warning("Continuing without database persistence (in-memory mode)")
    
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
    
    # Initialize orchestrator - only use database if it was initialized
    orchestrator = PurpleOrchestrator(
        engine=llm_engine,
        vector_store=vector_store,
        max_steps=settings.agent.max_steps,
        safe_mode=settings.agent.safe_mode,
        use_database=db_initialized,
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
    
    # Shutdown orchestrator
    if orchestrator:
        await orchestrator.shutdown()
    
    # Close database connection
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=__app_name__,
    description="Autonomous Purple Team cybersecurity simulation framework",
    version=__version__,
    lifespan=lifespan,
)


# CORS middleware for frontend access - SECURED CONFIGURATION
# In production, set CORS_ORIGINS environment variable to your actual frontend domains
def get_cors_origins() -> list[str]:
    """Get allowed CORS origins from environment or settings.
    
    Security: Never use ["*"] with allow_credentials=True
    """
    settings = get_settings()
    
    # Check for environment variable override
    cors_origins = os.environ.get("CORS_ORIGINS", "")
    if cors_origins:
        return [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    
    # Default development origins - should be overridden in production
    if settings.app.debug:
        return [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]
    
    # Production: require explicit configuration
    logger.warning(
        "CORS_ORIGINS not set in production mode. "
        "Set the CORS_ORIGINS environment variable to your frontend domains."
    )
    return []


allowed_origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Required for cookies/authorization headers
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
    max_age=600,  # Cache preflight requests for 10 minutes
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal error details in production
    settings = get_settings()
    detail = str(exc) if settings.app.debug else "Internal server error"
    
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
    )


@app.get("/", dependencies=[Depends(rate_limit_dependency)])
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
    Note: This endpoint is unauthenticated for health monitoring systems.
    """
    return {
        "status": "healthy",
        "version": __version__,
        "llm_configured": llm_engine.is_configured() if llm_engine else False,
        "vector_store_ready": vector_store is not None,
        "orchestrator_ready": orchestrator is not None,
        "feedback_store_ready": feedback_store is not None,
    }


@app.get("/status", dependencies=[Depends(rate_limit_dependency)])
async def status(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Detailed status endpoint.
    
    Requires authentication.
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


# Token endpoint for authentication
@app.post("/auth/token", dependencies=[Depends(rate_limit_dependency)])
async def create_token(request: Request) -> dict:
    """Create an access token.
    
    In a production system, this would validate credentials against
    a user database or external authentication provider.
    
    For now, this creates a token for a demo user.
    TODO: Implement proper credential validation.
    """
    from purple_team_gpt.backend.security import create_access_token
    
    # TODO: Implement proper authentication
    # For development, create a token with a default user
    settings = get_settings()
    
    if not settings.app.debug:
        raise HTTPException(
            status_code=501,
            detail="Authentication endpoint not configured for production",
        )
    
    # Development mode: create token for demo user
    token_data = {
        "sub": "demo_user",
        "roles": ["user"],
    }
    
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# Include routers
from purple_team_gpt.backend.routers import sessions, websocket, feedback, llm

app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])