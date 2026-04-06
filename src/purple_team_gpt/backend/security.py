"""Security utilities for authentication and authorization.

This module provides:
- Password hashing and verification using bcrypt
- JWT token generation and validation
- Rate limiting
- Input validation
- Security decorators for FastAPI endpoints
"""

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import bcrypt

from purple_team_gpt.config import get_settings


# ============================================================================
# Password Hashing
# ============================================================================


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt hashed password string
    """
    # Generate salt and hash the password
    # bcrypt automatically handles salt generation and storage
    salt = bcrypt.gensalt(rounds=12)  # Cost factor of 12 for security
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# Security scheme for OpenAPI
security = HTTPBearer(auto_error=False)


@dataclass
class RateLimitEntry:
    """Rate limit tracking entry."""

    count: int = 0
    window_start: float = 0.0


@dataclass
class RateLimiter:
    """Simple in-memory rate limiter.

    Uses sliding window algorithm for rate limiting.
    For production, consider using Redis for distributed rate limiting.
    """

    max_requests: int = 100
    window_seconds: int = 60
    _entries: Dict[str, RateLimitEntry] = field(default_factory=lambda: defaultdict(RateLimitEntry))

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (e.g., IP address or user ID)

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_seconds)
        """
        current_time = time.time()
        entry = self._entries[key]

        # Check if window has expired
        if current_time - entry.window_start >= self.window_seconds:
            entry.count = 0
            entry.window_start = current_time

        # Check limit
        if entry.count >= self.max_requests:
            reset_seconds = int(self.window_seconds - (current_time - entry.window_start))
            return False, 0, reset_seconds

        # Increment and allow
        entry.count += 1
        remaining = self.max_requests - entry.count
        reset_seconds = int(self.window_seconds - (current_time - entry.window_start))

        return True, remaining, reset_seconds

    def cleanup_expired(self, max_age_multiplier: float = 2.0) -> int:
        """Clean up expired entries to prevent memory leak.

        Args:
            max_age_multiplier: Multiplier for window_seconds to determine max age

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        max_age = self.window_seconds * max_age_multiplier
        expired_keys = [
            key
            for key, entry in self._entries.items()
            if current_time - entry.window_start > max_age
        ]

        for key in expired_keys:
            del self._entries[key]

        return len(expired_keys)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        _rate_limiter = RateLimiter(
            max_requests=settings.app.rate_limit_requests,
            window_seconds=settings.app.rate_limit_window_seconds,
        )
    return _rate_limiter


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.app.jwt_expire_minutes)

    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.app.secret_key,
        algorithm=settings.app.jwt_algorithm,
    )

    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Decoded payload dictionary

    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.app.secret_key,
            algorithms=[settings.app.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """FastAPI dependency to get the current authenticated user.

    Args:
        credentials: HTTP Bearer credentials from the request

    Returns:
        User payload from the JWT token

    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    return verify_token(token)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency to optionally get the current user.

    Returns None if not authenticated, instead of raising an exception.

    Args:
        credentials: HTTP Bearer credentials from the request

    Returns:
        User payload from the JWT token, or None if not authenticated
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        return verify_token(token)
    except HTTPException:
        return None


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request.

    Handles X-Forwarded-For header for reverse proxy setups.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address string
    """
    # Check X-Forwarded-For header (for reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def check_rate_limit(request: Request) -> Dict[str, int]:
    """Check rate limit for the current request.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with rate limit info

    Raises:
        HTTPException: If rate limit exceeded
    """
    limiter = get_rate_limiter()
    client_ip = get_client_ip(request)

    is_allowed, remaining, reset_seconds = limiter.is_allowed(client_ip)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_seconds} seconds.",
            headers={
                "X-RateLimit-Limit": str(limiter.max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_seconds),
            },
        )

    return {
        "limit": limiter.max_requests,
        "remaining": remaining,
        "reset": reset_seconds,
    }


# Dependency for rate-limited endpoints
async def rate_limit_dependency(request: Request) -> Dict[str, int]:
    """FastAPI dependency for rate limiting."""
    return check_rate_limit(request)


def require_auth(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Combined dependency for authenticated and rate-limited endpoints.

    Args:
        request: FastAPI request object
        current_user: Authenticated user from JWT

    Returns:
        User payload
    """
    # Check rate limit
    check_rate_limit(request)
    return current_user


# Input validation utilities
def validate_session_id(session_id: str) -> str:
    """Validate session ID format to prevent injection.

    Args:
        session_id: Session ID to validate

    Returns:
        Validated session ID

    Raises:
        HTTPException: If validation fails
    """
    import re

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID is required",
        )

    # Only allow alphanumeric, hyphens, and underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    # Limit length
    if len(session_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID too long",
        )

    return session_id


def validate_target(target: str) -> str:
    """Validate target specification to prevent command injection.

    Args:
        target: Target specification (IP, hostname, URL)

    Returns:
        Validated target

    Raises:
        HTTPException: If validation fails
    """
    import re

    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target is required",
        )

    # Limit length
    if len(target) > 512:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target specification too long",
        )

    # Block dangerous characters that could lead to command injection
    dangerous_patterns = [
        r";",  # Command separator
        r"\|",  # Pipe
        r"`",  # Command substitution
        r"\$\(",  # Command substitution
        r"&",  # Background execution
        r">",  # Redirection
        r"<",  # Redirection
        r"\n",  # Newline
        r"\r",  # Carriage return
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, target):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid characters in target specification",
            )

    return target


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize general text input.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text

    Raises:
        HTTPException: If validation fails
    """
    if not text:
        return ""

    if len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input exceeds maximum length of {max_length} characters",
        )

    # Remove null bytes
    text = text.replace("\x00", "")

    return text.strip()
