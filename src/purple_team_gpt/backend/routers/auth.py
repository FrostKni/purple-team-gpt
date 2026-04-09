"""Authentication endpoints.

This module provides REST endpoints for:
- User registration
- User login with JWT token generation
- Getting current user info

All endpoints are under /api/v1/auth prefix.
"""

import os
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from purple_team_gpt.db.database import get_session_dependency
from purple_team_gpt.db.models import User
from purple_team_gpt.backend.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# In-memory user store for development mode (when database is unavailable)
_dev_users: dict = {}

def _is_dev_mode() -> bool:
    """Check if running in development mode without database."""
    return os.getenv("APP_ENV", "development") == "development" and len(_dev_users) >= 0


def _get_dev_user(email: str) -> Optional[dict]:
    """Get user from in-memory store."""
    return _dev_users.get(email)


def _create_dev_user(email: str, password: str, full_name: Optional[str] = None) -> dict:
    """Create user in in-memory store."""
    user_id = str(uuid.uuid4())
    _dev_users[email] = {
        "id": user_id,
        "email": email,
        "password_hash": get_password_hash(password),
        "full_name": full_name,
        "is_active": True,
        "is_verified": True,  # Auto-verify in dev mode
        "is_superuser": False,
        "created_at": datetime.now(timezone.utc),
    }
    return _dev_users[email]


# ============================================================================
# Request/Response Models
# ============================================================================


class UserCreate(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        return v


class UserLogin(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response model for user data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool = False
    created_at: Optional[datetime] = None


class Token(BaseModel):
    """Response model for authentication token."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_session_dependency)):
    """Register a new user.

    Creates a new user account with hashed password and returns
    a JWT token for immediate authentication.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Token with access_token and user info

    Raises:
        HTTPException: 400 if email already registered
    """
    # Try database first, fall back to in-memory for dev mode
    try:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )

        # Create new user
        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            is_active=True,
            is_verified=False,
            is_superuser=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Create access token
        access_token = create_access_token(data={"sub": user.email, "user_id": user.id})

        return Token(
            access_token=access_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
            ),
        )
    except Exception as e:
        # Fall back to in-memory storage for development mode
        if "no such table" in str(e) or "Database not initialized" in str(e):
            # Check if user exists in memory
            existing_user = _get_dev_user(user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
                )
            
            # Create user in memory
            user = _create_dev_user(user_data.email, user_data.password, user_data.full_name)
            
            # Create access token
            access_token = create_access_token(data={"sub": user["email"], "user_id": user["id"]})
            
            return Token(
                access_token=access_token,
                user=UserResponse(
                    id=user["id"],
                    email=user["email"],
                    full_name=user["full_name"],
                    is_active=user["is_active"],
                    is_verified=user["is_verified"],
                    created_at=user["created_at"],
                ),
            )
        raise


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_session_dependency)):
    """Authenticate user and return JWT token.

    Validates user credentials and returns a JWT token if valid.

    Args:
        credentials: User login credentials
        db: Database session

    Returns:
        Token with access_token and user info

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Try database first, fall back to in-memory for dev mode
    try:
        # Find user by email
        result = await db.execute(select(User).where(User.email == credentials.email))
        user = result.scalar_one_or_none()

        # Verify user exists and password is correct
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()

        # Create access token
        access_token = create_access_token(data={"sub": user.email, "user_id": user.id})

        return Token(
            access_token=access_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
            ),
        )
    except Exception as e:
        # Fall back to in-memory storage for development mode
        if "no such table" in str(e) or "Database not initialized" in str(e):
            # Find user in memory
            user = _get_dev_user(credentials.email)
            
            if not user or not verify_password(credentials.password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Create access token
            access_token = create_access_token(data={"sub": user["email"], "user_id": user["id"]})
            
            return Token(
                access_token=access_token,
                user=UserResponse(
                    id=user["id"],
                    email=user["email"],
                    full_name=user["full_name"],
                    is_active=user["is_active"],
                    is_verified=user["is_verified"],
                    created_at=user["created_at"],
                ),
            )
        raise


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session_dependency),
):
    """Get current authenticated user info.

    Returns the user profile for the authenticated user.

    Args:
        current_user: Current user from JWT token
        db: Database session

    Returns:
        User profile data

    Raises:
        HTTPException: 401 if not authenticated
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get full user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )
