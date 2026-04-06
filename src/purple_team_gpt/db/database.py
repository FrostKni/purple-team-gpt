"""Async SQLAlchemy database configuration.

This module provides the async engine, session factory, and dependency
injection for database sessions in FastAPI.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from purple_team_gpt.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class DatabaseSessionManager:
    """Manages database engine and session lifecycle.
    
    Provides a centralized way to manage database connections
    and sessions for the application.
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    async def init(self, database_url: str, debug: bool = False) -> None:
        """Initialize the engine and session factory."""
        if self._engine is not None:
            logger.warning("Database already initialized")
            return
        
        # Build engine kwargs - only include pool settings when not using NullPool
        engine_kwargs = {"echo": debug}
        
        # For PostgreSQL, use connection pooling; for SQLite, use NullPool
        if "sqlite" in database_url.lower():
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.update({
                "pool_pre_ping": True,
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600,
            })
        
        self._engine = create_async_engine(database_url, **engine_kwargs)
        
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info(f"Database session manager initialized")
    
    async def close(self) -> None:
        """Close the engine."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database session manager closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Global session manager
_session_manager = DatabaseSessionManager()

# Legacy globals for backward compatibility
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def create_engine(database_url: str, debug: bool = False) -> AsyncEngine:
    """Create a new async engine.
    
    Args:
        database_url: Database connection URL
        debug: Enable SQL echo
        
    Returns:
        AsyncEngine instance
    """
    engine_kwargs = {"echo": debug}
    
    # For PostgreSQL, use connection pooling; for SQLite, use NullPool
    if "sqlite" in database_url.lower():
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs.update({
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 3600,
        })
    
    return create_async_engine(database_url, **engine_kwargs)


async def check_db_connection() -> bool:
    """Check if database connection is healthy.
    
    Returns:
        True if connection is healthy, False otherwise
    """
    global _engine
    if _engine is None:
        return False
    
    try:
        async with _engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_url() -> str:
    """Build the async database URL from settings.
    
    Returns:
        Async PostgreSQL connection URL
    """
    settings = get_settings()
    return settings.db.async_url


# Property aliases for backward compatibility
def async_engine() -> Optional[AsyncEngine]:
    """Get the database engine (alias for get_engine)."""
    return _engine


def AsyncSessionLocal() -> Optional[async_sessionmaker[AsyncSession]]:
    """Get the session factory."""
    return _session_factory


def get_engine() -> Optional[AsyncEngine]:
    """Get the database engine.
    
    Returns:
        AsyncEngine instance or None if not initialized
    """
    return _engine


async def init_db() -> None:
    """Initialize the database engine and session factory.
    
    This should be called during application startup.
    Creates the engine with connection pooling and creates tables
    if they don't exist.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        logger.warning("Database already initialized")
        return
    
    database_url = get_database_url()
    settings = get_settings()
    
    # Build engine kwargs - only include pool settings when not using NullPool
    engine_kwargs = {
        "echo": settings.app.debug and settings.app.log_level == "DEBUG",
    }
    
    # For PostgreSQL, use connection pooling with proper settings
    # NullPool disables pooling (useful for SQLite or serverless)
    # For production PostgreSQL, we want connection pooling
    if "sqlite" in database_url.lower():
        # SQLite doesn't support connection pooling
        engine_kwargs["poolclass"] = NullPool
    else:
        # PostgreSQL with connection pooling
        engine_kwargs.update({
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        })
    
    _engine = create_async_engine(database_url, **engine_kwargs)
    
    # Create session factory
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Import models and create tables
    from purple_team_gpt.db.models import Base as ModelsBase
    
    async with _engine.begin() as conn:
        await conn.run_sync(ModelsBase.metadata.create_all)
    
    logger.info(f"Database initialized: {database_url.split('@')[-1]}")


async def close_db() -> None:
    """Close the database engine.
    
    This should be called during application shutdown.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connection closed")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session.
    
    This is the primary way to get a database session.
    Use as an async context manager:
    
        async with get_session() as session:
            repo = SessionRepository(session)
            session_obj = await repo.get_session(session_id)
    
    Yields:
        AsyncSession instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    session = _session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Alias for backward compatibility
get_async_session = get_session

# Alias for context manager usage
get_session_context = get_session


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.
    
    Use with Depends() for automatic session management:
    
        @router.get("/sessions/{session_id}")
        async def get_session(
            session_id: str,
            db: AsyncSession = Depends(get_session_dependency)
        ):
            repo = SessionRepository(db)
            return await repo.get_session(session_id)
    
    Yields:
        AsyncSession instance
    """
    async with get_session() as session:
        yield session