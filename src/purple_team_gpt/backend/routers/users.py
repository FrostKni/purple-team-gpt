"""User management endpoints.

This module provides REST endpoints for:
- Listing all users (paginated)
- Getting a user by ID

All endpoints require authentication and are under /api/v1/users prefix.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from purple_team_gpt.db.database import get_session_dependency
from purple_team_gpt.db.models import User
from purple_team_gpt.backend.security import get_current_user
from purple_team_gpt.backend.routers.auth import UserResponse


router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session_dependency),
):
    """List all users (requires authentication).

    Returns a paginated list of all users in the system.

    Args:
        skip: Number of records to skip (pagination offset)
        limit: Maximum number of records to return
        current_user: Current authenticated user from JWT token
        db: Database session

    Returns:
        List of user records

    Raises:
        HTTPException: 401 if not authenticated
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session_dependency),
):
    """Get user by ID.

    Returns a specific user by their ID.

    Args:
        user_id: UUID of the user to retrieve
        current_user: Current authenticated user from JWT token
        db: Database session

    Returns:
        User record

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if user not found
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.model_validate(user)
