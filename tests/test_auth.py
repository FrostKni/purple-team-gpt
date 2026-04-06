"""Tests for authentication endpoints.

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
    "test-secret-key-for-auth-tests-very-long-key-minimum-64-chars-padding-here"
)
os.environ["APP_DEBUG"] = "true"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["LLM_DEFAULT_PROVIDER"] = "openai"
os.environ["LLM_DEFAULT_MODEL"] = "gpt-4o"

# Add src to path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from typing import AsyncGenerator
from datetime import datetime

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
async def app_with_auth(test_session: AsyncSession):
    """Create FastAPI app with auth router."""
    from purple_team_gpt.backend.routers.auth import router as auth_router
    from purple_team_gpt.db.database import get_session_dependency

    # Create app
    app = FastAPI()

    # Override database dependency
    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session_dependency] = override_get_session

    # Include auth router
    app.include_router(auth_router)

    yield app

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app_with_auth) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app_with_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Test: User Registration
# ============================================================================


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration creates new user.

    GREEN: This test should pass after implementation.
    """
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "SecurePass123!", "full_name": "Test User"},
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    # Token response has access_token, token_type, and user
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["full_name"] == "Test User"
    assert "id" in data["user"]
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test that registering with duplicate email fails."""
    # First registration should succeed
    response1 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "SecurePass123!",
            "full_name": "First User",
        },
    )
    assert response1.status_code == 201

    # Second registration with same email should fail
    response2 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "AnotherPass456!",
            "full_name": "Second User",
        },
    )
    assert response2.status_code == 400
    assert "already registered" in response2.json()["detail"].lower()


# ============================================================================
# Test: User Login
# ============================================================================


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    """Test user login returns valid JWT token."""
    # First register a user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "SecurePass123!",
            "full_name": "Login User",
        },
    )
    assert register_response.status_code == 201

    # Then login
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": "SecurePass123!"}
    )

    assert login_response.status_code == 200, (
        f"Expected 200, got {login_response.status_code}: {login_response.text}"
    )
    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test that login with wrong password fails."""
    # First register a user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
            "full_name": "Wrong Pass User",
        },
    )
    assert register_response.status_code == 201

    # Try to login with wrong password
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "wrongpass@example.com", "password": "WrongPassword!"}
    )

    assert login_response.status_code == 401
    assert "invalid" in login_response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test that login with nonexistent user fails."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "SomePassword123!"},
    )

    assert login_response.status_code == 401


# ============================================================================
# Test: Get Current User (/me)
# ============================================================================


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """Test getting current user info with valid token."""
    # Register and login to get token
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "SecurePass123!", "full_name": "Me User"},
    )
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]

    # Get current user info
    me_response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_response.status_code == 200, (
        f"Expected 200, got {me_response.status_code}: {me_response.text}"
    )
    data = me_response.json()
    assert data["email"] == "me@example.com"
    assert data["full_name"] == "Me User"
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    """Test that getting current user without token fails."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    """Test that getting current user with invalid token fails."""
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401
