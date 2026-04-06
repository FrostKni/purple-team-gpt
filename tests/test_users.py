"""Tests for user management endpoints.

Following TDD: These tests are written FIRST, then code is implemented to pass them.
"""

import os
import sys

# IMPORTANT: Unset conflicting environment variables BEFORE any imports
# The system has AGENT=1 set which conflicts with Settings.agent field
if "AGENT" in os.environ:
    del os.environ["AGENT"]

# Set required environment variables BEFORE any imports
os.environ["APP_SECRET_KEY"] = (
    "test-secret-key-for-users-tests-very-long-key-minimum-64-chars-padding-here"
)
os.environ["APP_DEBUG"] = "true"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["LLM_DEFAULT_PROVIDER"] = "openai"
os.environ["LLM_DEFAULT_MODEL"] = "gpt-4o"

# Add src to path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from purple_team_gpt.db.database import Base
from purple_team_gpt.db.models import User


# Test database setup - use SQLite without PostgreSQL-specific constraints
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine with SQLite-compatible schema."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables without PostgreSQL-specific CHECK constraints
    async with engine.begin() as conn:
        # Create users table with SQLite-compatible schema
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                avatar_url VARCHAR(500),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_verified BOOLEAN NOT NULL DEFAULT 0,
                is_superuser BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                last_login_at DATETIME,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until DATETIME,
                mfa_enabled BOOLEAN NOT NULL DEFAULT 0,
                mfa_secret VARCHAR(255)
            )
        """)
        )

    yield engine

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS users"))

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def app_with_routers(test_session: AsyncSession):
    """Create FastAPI app with auth and users routers."""
    from purple_team_gpt.backend.routers.auth import router as auth_router
    from purple_team_gpt.backend.routers.users import router as users_router
    from purple_team_gpt.db.database import get_session_dependency

    # Create app
    app = FastAPI()

    # Override database dependency
    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session_dependency] = override_get_session

    # Include routers
    app.include_router(auth_router)
    app.include_router(users_router)

    yield app

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app_with_routers) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app_with_routers)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Test: List Users
# ============================================================================


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient):
    """Test listing all users returns list with authentication.

    RED: This test should fail until users router is implemented.
    """
    # Register user first
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "user1@example.com", "password": "Pass123!", "full_name": "User One"},
    )
    assert register_response.status_code == 201

    # Login to get token
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "user1@example.com", "password": "Pass123!"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # List users with authentication
    response = await client.get("/api/v1/users/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Verify user data structure
    user = data[0]
    assert "id" in user
    assert "email" in user
    assert "password" not in user
    assert "password_hash" not in user


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client: AsyncClient):
    """Test that listing users without authentication fails.

    RED: This test should fail until users router is implemented.
    """
    response = await client.get("/api/v1/users/")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_pagination(client: AsyncClient):
    """Test listing users with pagination parameters.

    RED: This test should fail until users router is implemented.
    """
    # Register and login to get token
    register_response = await client.post(
        "/api/v1/auth/register", json={"email": "paginator@example.com", "password": "Pass123!"}
    )
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]

    # List users with pagination
    response = await client.get(
        "/api/v1/users/?skip=0&limit=10", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


# ============================================================================
# Test: Get User by ID
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient):
    """Test getting a specific user by ID.

    RED: This test should fail until users router is implemented.
    """
    # Register user first
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "getuser@example.com", "password": "Pass123!", "full_name": "Get User"},
    )
    assert register_response.status_code == 201
    user_data = register_response.json()["user"]
    user_id = user_data["id"]
    token = register_response.json()["access_token"]

    # Get user by ID
    response = await client.get(
        f"/api/v1/users/{user_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "getuser@example.com"
    assert data["full_name"] == "Get User"
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    """Test getting a non-existent user returns 404.

    RED: This test should fail until users router is implemented.
    """
    # Register and login to get token
    register_response = await client.post(
        "/api/v1/auth/register", json={"email": "notfound@example.com", "password": "Pass123!"}
    )
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]

    # Try to get non-existent user
    fake_user_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/v1/users/{fake_user_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_user_unauthenticated(client: AsyncClient):
    """Test that getting user without authentication fails.

    RED: This test should fail until users router is implemented.
    """
    response = await client.get("/api/v1/users/some-id")

    assert response.status_code == 401
