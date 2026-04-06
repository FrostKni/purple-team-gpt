# Purple Team GPT Security Architecture

## Executive Summary

This document outlines the production-ready security architecture for Purple Team GPT, addressing identified vulnerabilities and establishing defense-in-depth controls.

## 1. Current Security Issues Identified

### 1.1 Critical Vulnerabilities

| Issue | Severity | Description |
|-------|----------|-------------|
| No Authentication | CRITICAL | All API endpoints are unauthenticated |
| No Authorization | CRITICAL | No role-based access control |
| SSRF via LLM Config | HIGH | Arbitrary base_url allowed in endpoint configuration |
| Command Injection Risk | HIGH | Tool execution lacks proper validation |
| Sensitive Data in Memory | HIGH | API keys stored without encryption |
| No Rate Limiting | MEDIUM | Vulnerable to DoS and abuse |
| Permissive CORS | MEDIUM | `allow_headers=["*"]` allows any header |
| WebSocket No Auth | HIGH | WebSocket connections unauthenticated |
| No Audit Logging | MEDIUM | Security events not logged |

### 1.2 Architecture Issues

- Global state via module-level variables
- No dependency injection for security services
- No session management for users
- No encryption at rest for sensitive data

---

## 2. JWT-Based Authentication System

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Request                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Rate Limiting Middleware                      │
│                    (Redis-backed sliding window)                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    JWT Authentication Middleware                 │
│                    - Token validation                            │
│                    - Signature verification                      │
│                    - Expiration check                            │
│                    - Revocation check (Redis blacklist)          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Authorization Middleware                      │
│                    - Role-based access control                   │
│                    - Resource ownership validation               │
│                    - Permission check                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Input Validation Layer                        │
│                    - Pydantic models with constraints            │
│                    - Command sanitization                        │
│                    - URL/Path validation                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Business Logic                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Token Structure

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-id-2024-01"
  },
  "payload": {
    "sub": "user-uuid",
    "iat": 1704067200,
    "exp": 1704153600,
    "jti": "unique-token-id",
    "roles": ["analyst"],
    "permissions": ["sessions:read", "sessions:write", "findings:read"],
    "org_id": "org-uuid",
    "session_id": "auth-session-uuid"
  },
  "signature": "..."
}
```

### 2.3 Token Lifecycle

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│   Access Token │     │  Refresh Token │     │  API Key       │
│   (15 min TTL) │     │  (7 day TTL)   │     │  (90 day TTL)  │
└────────────────┘     └────────────────┘     └────────────────┘
        │                      │                      │
        │                      │                      │
        ▼                      ▼                      ▼
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│ Short-lived    │     │ Single-use     │     │ For service    │
│ API requests   │     │ Rotated on     │     │ accounts and   │
│                │     │ refresh        │     │ automation     │
└────────────────┘     └────────────────┘     └────────────────┘
```

### 2.4 Implementation

```python
# src/purple_team_gpt/security/auth.py

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
import secrets
import hashlib

from pydantic import BaseModel, Field
from jose import jwt, JWTError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    SERVICE = "service"


class Permission(str, Enum):
    """Granular permissions."""
    # Session permissions
    SESSIONS_READ = "sessions:read"
    SESSIONS_WRITE = "sessions:write"
    SESSIONS_DELETE = "sessions:delete"
    SESSIONS_EXECUTE = "sessions:execute"
    
    # Finding permissions
    FINDINGS_READ = "findings:read"
    FINDINGS_WRITE = "findings:write"
    FINDINGS_EXPORT = "findings:export"
    
    # LLM permissions
    LLM_CONFIGURE = "llm:configure"
    LLM_TEST = "llm:test"
    
    # Admin permissions
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"
    SYSTEM_CONFIGURE = "system:configure"


# Role to permission mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: {
        Permission.SESSIONS_READ, Permission.SESSIONS_WRITE,
        Permission.SESSIONS_DELETE, Permission.SESSIONS_EXECUTE,
        Permission.FINDINGS_READ, Permission.FINDINGS_WRITE,
        Permission.FINDINGS_EXPORT,
        Permission.LLM_CONFIGURE, Permission.LLM_TEST,
        Permission.USERS_MANAGE, Permission.AUDIT_READ,
        Permission.SYSTEM_CONFIGURE,
    },
    UserRole.ANALYST: {
        Permission.SESSIONS_READ, Permission.SESSIONS_WRITE,
        Permission.SESSIONS_EXECUTE,
        Permission.FINDINGS_READ, Permission.FINDINGS_WRITE,
        Permission.FINDINGS_EXPORT,
        Permission.LLM_TEST,
    },
    UserRole.VIEWER: {
        Permission.SESSIONS_READ,
        Permission.FINDINGS_READ,
    },
    UserRole.SERVICE: {
        Permission.SESSIONS_READ, Permission.SESSIONS_WRITE,
        Permission.SESSIONS_EXECUTE,
        Permission.FINDINGS_READ, Permission.FINDINGS_WRITE,
    },
}


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # User ID
    iat: int
    exp: int
    jti: str  # Unique token ID for revocation
    roles: List[UserRole]
    permissions: List[Permission]
    org_id: Optional[str] = None
    session_id: Optional[str] = None


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class JWTManager:
    """JWT token management with RS256 signing."""
    
    ALGORITHM = "RS256"
    ACCESS_TOKEN_TTL = 900  # 15 minutes
    REFRESH_TOKEN_TTL = 604800  # 7 days
    
    def __init__(
        self,
        private_key_pem: str,
        public_key_pem: str,
        issuer: str,
        audience: str,
        redis_client: Optional[any] = None,
    ):
        self.private_key = private_key_pem
        self.public_key = public_key_pem
        self.issuer = issuer
        self.audience = audience
        self.redis = redis_client
        
    def create_access_token(
        self,
        user_id: str,
        roles: List[UserRole],
        org_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Create a short-lived access token."""
        now = datetime.utcnow()
        permissions = self._get_permissions_for_roles(roles)
        
        payload = {
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.ACCESS_TOKEN_TTL)).timestamp()),
            "jti": secrets.token_urlsafe(32),
            "iss": self.issuer,
            "aud": self.audience,
            "roles": [r.value for r in roles],
            "permissions": [p.value for p in permissions],
        }
        
        if org_id:
            payload["org_id"] = org_id
        if session_id:
            payload["session_id"] = session_id
            
        return jwt.encode(payload, self.private_key, algorithm=self.ALGORITHM)
    
    def create_refresh_token(
        self,
        user_id: str,
        session_id: str,
    ) -> str:
        """Create a long-lived refresh token."""
        now = datetime.utcnow()
        
        payload = {
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.REFRESH_TOKEN_TTL)).timestamp()),
            "jti": secrets.token_urlsafe(32),
            "iss": self.issuer,
            "aud": self.audience,
            "type": "refresh",
            "session_id": session_id,
        }
        
        return jwt.encode(payload, self.private_key, algorithm=self.ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.ALGORITHM],
                issuer=self.issuer,
                audience=self.audience,
            )
            
            # Check if token is revoked
            if self.redis:
                jti = payload.get("jti")
                if self.redis.exists(f"revoked:{jti}"):
                    return None
            
            return TokenPayload(
                sub=payload["sub"],
                iat=payload["iat"],
                exp=payload["exp"],
                jti=payload["jti"],
                roles=[UserRole(r) for r in payload.get("roles", [])],
                permissions=[Permission(p) for p in payload.get("permissions", [])],
                org_id=payload.get("org_id"),
                session_id=payload.get("session_id"),
            )
        except JWTError:
            return None
    
    def revoke_token(self, jti: str, ttl: int = None) -> None:
        """Add token to revocation list."""
        if self.redis:
            ttl = ttl or self.REFRESH_TOKEN_TTL
            self.redis.setex(f"revoked:{jti}", ttl, "1")
    
    def _get_permissions_for_roles(self, roles: List[UserRole]) -> set[Permission]:
        """Aggregate permissions from all roles."""
        permissions = set()
        for role in roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        return permissions
```

---

## 3. Authorization Middleware

### 3.1 Role-Based Access Control (RBAC)

```python
# src/purple_team_gpt/security/authorization.py

from typing import Optional, List, Callable
from functools import wraps

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth import JWTManager, TokenPayload, Permission, UserRole


security = HTTPBearer(auto_error=False)


class AuthContext:
    """Authentication context for the current request."""
    
    def __init__(
        self,
        user_id: str,
        roles: List[UserRole],
        permissions: List[Permission],
        org_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.roles = roles
        self.permissions = set(permissions)
        self.org_id = org_id
        self.session_id = session_id
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions."""
        return all(p in self.permissions for p in permissions)
    
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return UserRole.ADMIN in self.roles
    
    def can_access_resource(self, resource_org_id: Optional[str]) -> bool:
        """Check if user can access a resource (org-based)."""
        if self.is_admin():
            return True
        if not resource_org_id:
            return True
        return self.org_id == resource_org_id


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthContext:
    """Extract and validate the current user from the JWT token."""
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    jwt_manager: JWTManager = request.app.state.jwt_manager
    payload = jwt_manager.verify_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return AuthContext(
        user_id=payload.sub,
        roles=payload.roles,
        permissions=payload.permissions,
        org_id=payload.org_id,
        session_id=payload.session_id,
    )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthContext]:
    """Get current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    
    jwt_manager: JWTManager = request.app.state.jwt_manager
    payload = jwt_manager.verify_token(credentials.credentials)
    
    if not payload:
        return None
    
    return AuthContext(
        user_id=payload.sub,
        roles=payload.roles,
        permissions=payload.permissions,
        org_id=payload.org_id,
        session_id=payload.session_id,
    )


def require_permissions(*permissions: Permission):
    """Decorator to require specific permissions for an endpoint."""
    
    async def permission_checker(
        auth: AuthContext = Depends(get_current_user),
    ) -> AuthContext:
        if not auth.has_all_permissions(list(permissions)):
            raise HTTPException(
                status_code=403,
                detail=f"Required permissions: {[p.value for p in permissions]}",
            )
        return auth
    
    return Depends(permission_checker)


def require_any_permission(*permissions: Permission):
    """Decorator to require any of the specified permissions."""
    
    async def permission_checker(
        auth: AuthContext = Depends(get_current_user),
    ) -> AuthContext:
        if not auth.has_any_permission(list(permissions)):
            raise HTTPException(
                status_code=403,
                detail=f"Required one of: {[p.value for p in permissions]}",
            )
        return auth
    
    return Depends(permission_checker)


def require_roles(*roles: UserRole):
    """Decorator to require specific roles."""
    
    async def role_checker(
        auth: AuthContext = Depends(get_current_user),
    ) -> AuthContext:
        if not any(r in auth.roles for r in roles):
            raise HTTPException(
                status_code=403,
                detail=f"Required roles: {[r.value for r in roles]}",
            )
        return auth
    
    return Depends(role_checker)
```

### 3.2 Resource-Based Authorization

```python
# src/purple_team_gpt/security/resource_auth.py

from typing import Optional
from abc import ABC, abstractmethod

from fastapi import HTTPException

from .authorization import AuthContext


class ResourceAuthorization(ABC):
    """Base class for resource-level authorization."""
    
    @abstractmethod
    async def can_read(self, auth: AuthContext, resource_id: str) -> bool:
        """Check read access."""
        pass
    
    @abstractmethod
    async def can_write(self, auth: AuthContext, resource_id: str) -> bool:
        """Check write access."""
        pass
    
    @abstractmethod
    async def can_delete(self, auth: AuthContext, resource_id: str) -> bool:
        """Check delete access."""
        pass


class SessionAuthorization(ResourceAuthorization):
    """Authorization for session resources."""
    
    def __init__(self, session_store):
        self.session_store = session_store
    
    async def can_read(self, auth: AuthContext, session_id: str) -> bool:
        """Check if user can read a session."""
        if auth.is_admin():
            return True
        
        session = await self.session_store.get_session(session_id)
        if not session:
            return False
        
        # Check org ownership
        return auth.can_access_resource(session.org_id)
    
    async def can_write(self, auth: AuthContext, session_id: str) -> bool:
        """Check if user can modify a session."""
        if not auth.has_permission(Permission.SESSIONS_WRITE):
            return False
        
        return await self.can_read(auth, session_id)
    
    async def can_delete(self, auth: AuthContext, session_id: str) -> bool:
        """Check if user can delete a session."""
        if not auth.has_permission(Permission.SESSIONS_DELETE):
            return False
        
        return await self.can_read(auth, session_id)
    
    async def can_execute(self, auth: AuthContext, session_id: str) -> bool:
        """Check if user can execute/stop/pause a session."""
        if not auth.has_permission(Permission.SESSIONS_EXECUTE):
            return False
        
        return await self.can_read(auth, session_id)


async def check_session_access(
    session_id: str,
    auth: AuthContext,
    action: str,  # "read", "write", "delete", "execute"
    session_auth: SessionAuthorization,
) -> None:
    """Check session access or raise 403/404."""
    
    method = getattr(session_auth, f"can_{action}", None)
    if not method:
        raise ValueError(f"Unknown action: {action}")
    
    if not await method(auth, session_id):
        # Don't reveal existence if no read access
        if action == "read":
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=403, detail="Access denied")
```

---

## 4. Input Validation Layer

### 4.1 Validation Framework

```python
# src/purple_team_gpt/security/validation.py

import re
import validators
from typing import Optional, List, Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class SecurityValidationError(Exception):
    """Custom validation error for security violations."""
    pass


# Allowed URL schemes for LLM endpoints
ALLOWED_SCHEMES = {"http", "https"}

# Blocked IP ranges (SSRF prevention)
BLOCKED_IP_RANGES = [
    "127.0.0.0/8",      # Loopback
    "10.0.0.0/8",       # Private
    "172.16.0.0/12",    # Private
    "192.168.0.0/16",   # Private
    "169.254.0.0/16",   # Link-local
    "0.0.0.0/8",        # Current network
    "224.0.0.0/4",      # Multicast
    "240.0.0.0/4",      # Reserved
]

# Dangerous command patterns
DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r">\s*/dev/",
    r"mkfs",
    r"dd\s+if=",
    r":(){ :|:& };:",  # Fork bomb
    r"chmod\s+777",
    r"chown\s+.*root",
    r"sudo\s+",
    r"su\s+",
    r">\s*/etc/",
    r"/etc/shadow",
    r"/etc/passwd",
]


class ValidatedString:
    """Validated string with length and content constraints."""
    
    MAX_LENGTH = 10000
    MIN_LENGTH = 1
    
    @classmethod
    def validate(
        cls,
        value: str,
        max_length: int = None,
        min_length: int = None,
        allow_html: bool = False,
        allow_special_chars: bool = True,
    ) -> str:
        """Validate a string with security constraints."""
        
        max_length = max_length or cls.MAX_LENGTH
        min_length = min_length or cls.MIN_LENGTH
        
        if not isinstance(value, str):
            raise SecurityValidationError("Value must be a string")
        
        # Length check
        if len(value) < min_length:
            raise SecurityValidationError(f"Minimum length is {min_length}")
        if len(value) > max_length:
            raise SecurityValidationError(f"Maximum length is {max_length}")
        
        # Null byte injection
        if "\x00" in value:
            raise SecurityValidationError("Null bytes not allowed")
        
        # Control characters
        if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise SecurityValidationError("Control characters not allowed")
        
        # HTML injection (if not allowed)
        if not allow_html:
            if re.search(r"<[^>]+>", value):
                raise SecurityValidationError("HTML tags not allowed")
        
        return value.strip()


class URLValidator:
    """URL validation with SSRF prevention."""
    
    ALLOWED_SCHEMES = {"http", "https"}
    
    # Whitelist for allowed hosts (if configured)
    ALLOWED_HOSTS: Optional[set] = None
    
    @classmethod
    def validate(
        cls,
        url: str,
        allow_private_ips: bool = False,
        allowed_schemes: set = None,
    ) -> str:
        """Validate URL with SSRF protection."""
        
        allowed_schemes = allowed_schemes or cls.ALLOWED_SCHEMES
        
        try:
            parsed = urlparse(url.strip())
        except Exception:
            raise SecurityValidationError("Invalid URL format")
        
        # Scheme validation
        if parsed.scheme.lower() not in allowed_schemes:
            raise SecurityValidationError(
                f"URL scheme must be one of: {allowed_schemes}"
            )
        
        # Host validation
        host = parsed.hostname
        if not host:
            raise SecurityValidationError("URL must have a hostname")
        
        # Private IP check (SSRF prevention)
        if not allow_private_ips:
            import ipaddress
            
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_reserved:
                    raise SecurityValidationError(
                        "Private/internal IP addresses not allowed"
                    )
            except ValueError:
                # Not an IP address, continue with hostname checks
                pass
        
        # Host whitelist check (if configured)
        if cls.ALLOWED_HOSTS and host.lower() not in cls.ALLOWED_HOSTS:
            raise SecurityValidationError(
                f"Host '{host}' is not in allowed list"
            )
        
        return url


class CommandValidator:
    """Command validation for tool execution."""
    
    # Dangerous patterns
    BLOCKED_PATTERNS = [
        r"rm\s+-rf",
        r">\s*/dev/",
        r"mkfs",
        r"dd\s+if=",
        r":\(\)\s*\{",  # Fork bomb
        r"chmod\s+[0-7]*777",
        r">\s*/etc/",
        r"/etc/shadow",
        r"/etc/passwd",
        r"\$\([^)]+\)",  # Command substitution
        r"`[^`]+`",      # Backtick execution
        r"\|\s*bash",
        r"\|\s*sh",
        r";\s*rm",
        r"&&\s*rm",
    ]
    
    # Allowed tools whitelist
    ALLOWED_TOOLS: Optional[set] = None
    
    @classmethod
    def validate(cls, command: str, tool_name: str = None) -> str:
        """Validate a command for dangerous patterns."""
        
        # Tool whitelist check
        if cls.ALLOWED_TOOLS and tool_name:
            if tool_name not in cls.ALLOWED_TOOLS:
                raise SecurityValidationError(
                    f"Tool '{tool_name}' is not allowed"
                )
        
        # Check for dangerous patterns
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                raise SecurityValidationError(
                    f"Command contains blocked pattern"
                )
        
        return command


class TargetValidator:
    """Target validation for security assessments."""
    
    # Allowed target formats
    IP_PATTERN = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?$"
    DOMAIN_PATTERN = r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    
    # Require explicit scope authorization
    REQUIRE_SCOPE = True
    
    @classmethod
    def validate(
        cls,
        target: str,
        scope: str = None,
        authorized_targets: set = None,
    ) -> str:
        """Validate target with scope authorization."""
        
        # Basic format validation
        is_ip = re.match(cls.IP_PATTERN, target)
        is_domain = re.match(cls.DOMAIN_PATTERN, target)
        
        if not (is_ip or is_domain):
            raise SecurityValidationError(
                "Target must be a valid IP address, CIDR range, or domain name"
            )
        
        # Scope authorization check
        if cls.REQUIRE_SCOPE and not scope:
            raise SecurityValidationError(
                "Scope authorization is required for all targets"
            )
        
        # Target whitelist check (if configured)
        if authorized_targets:
            target_authorized = any(
                cls._target_in_scope(target, auth_scope)
                for auth_scope in authorized_targets
            )
            if not target_authorized:
                raise SecurityValidationError(
                    "Target is not in authorized scope"
                )
        
        return target
    
    @classmethod
    def _target_in_scope(cls, target: str, scope: str) -> bool:
        """Check if target falls within authorized scope."""
        import ipaddress
        
        # Simple string match
        if target == scope:
            return True
        
        # CIDR range check
        try:
            if "/" in scope:
                network = ipaddress.ip_network(scope, strict=False)
                ip = ipaddress.ip_address(target.split("/")[0])
                return ip in network
        except ValueError:
            pass
        
        # Domain wildcard check
        if scope.startswith("*."):
            domain_suffix = scope[1:]  # Remove *
            return target.endswith(domain_suffix)
        
        return False
```

### 4.2 Request Models with Validation

```python
# src/purple_team_gpt/schemas/requests.py

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator

from ..security.validation import (
    ValidatedString,
    URLValidator,
    CommandValidator,
    TargetValidator,
)


class SessionCreateRequest(BaseModel):
    """Request model for creating a new session with validation."""
    
    target: str = Field(..., description="Target system/network for assessment")
    scope: str = Field(..., description="Authorization scope and constraints")
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    
    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        return TargetValidator.validate(v)
    
    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        return ValidatedString.validate(v, max_length=5000)
    
    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Optional[Dict]) -> Optional[Dict]:
        if v is None:
            return v
        # Recursively validate string values in metadata
        def validate_dict(d: Dict) -> Dict:
            result = {}
            for k, val in d.items():
                if isinstance(val, str):
                    result[k] = ValidatedString.validate(val, max_length=1000)
                elif isinstance(val, dict):
                    result[k] = validate_dict(val)
                elif isinstance(val, list):
                    result[k] = [
                        ValidatedString.validate(item, max_length=1000)
                        if isinstance(item, str) else item
                        for item in val
                    ]
                else:
                    result[k] = val
            return result
        return validate_dict(v)


class EndpointCreateRequest(BaseModel):
    """Request model for creating an LLM endpoint with SSRF protection."""
    
    name: str = Field(..., min_length=1, max_length=100)
    api_key: Optional[str] = Field(default=None, max_length=200)
    base_url: str = Field(..., description="Base URL for the API")
    model: str = Field(..., min_length=1, max_length=100)
    enabled: bool = Field(default=True)
    timeout: int = Field(default=300, ge=1, le=3600)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Alphanumeric, dash, underscore only
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name must be alphanumeric with dashes and underscores")
        return v
    
    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        # Only allow public IPs/hostnames to prevent SSRF
        return URLValidator.validate(v, allow_private_ips=False)


class ToolExecutionRequest(BaseModel):
    """Request model for tool execution with command validation."""
    
    tool_name: str = Field(..., description="Name of the tool to execute")
    command: str = Field(..., description="Command to execute")
    timeout: int = Field(default=300, ge=1, le=1800)
    safe_mode: bool = Field(default=True)
    
    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        # Alphanumeric, dash, underscore only
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Invalid tool name format")
        return v
    
    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        return CommandValidator.validate(v)
    
    @model_validator(mode="after")
    def validate_safe_mode(self):
        if not self.safe_mode:
            # Extra validation when safe mode is disabled
            CommandValidator.validate(self.command, self.tool_name)
        return self
```

---

## 5. Rate Limiting Strategy

### 5.1 Rate Limiting Architecture

```python
# src/purple_team_gpt/security/rate_limiting.py

import time
import hashlib
from typing import Optional, Callable
from enum import Enum

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitScope(str, Enum):
    """Scope for rate limiting."""
    IP = "ip"           # Per IP address
    USER = "user"       # Per authenticated user
    GLOBAL = "global"   # Global across all requests
    ENDPOINT = "endpoint"  # Per endpoint


class RateLimitStrategy(str, Enum):
    """Rate limiting algorithms."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimiter:
    """Redis-backed rate limiter with multiple strategies."""
    
    def __init__(
        self,
        redis_client,
        strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
    ):
        self.redis = redis_client
        self.strategy = strategy
    
    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            Tuple of (is_allowed, metadata dict with remaining, reset_time, etc.)
        """
        
        if self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window(key, max_requests, window_seconds)
        elif self.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window(key, max_requests, window_seconds)
        else:
            return await self._token_bucket(key, max_requests, window_seconds)
    
    async def _sliding_window(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        """Sliding window rate limiting (most accurate)."""
        
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current entries
        pipe.zcard(key)
        
        # Add current request (score = timestamp)
        pipe.zadd(key, {str(now): now})
        
        # Set expiry
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        current_count = results[1]
        
        remaining = max(0, max_requests - current_count - 1)
        reset_time = int(now + window_seconds)
        
        is_allowed = current_count < max_requests
        
        return is_allowed, {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_time,
            "retry_after": reset_time - int(now) if not is_allowed else 0,
        }
    
    async def _fixed_window(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        """Fixed window rate limiting (simpler but less accurate)."""
        
        now = time.time()
        window_key = f"{key}:{int(now // window_seconds)}"
        
        current = await self.redis.incr(window_key)
        
        if current == 1:
            await self.redis.expire(window_key, window_seconds)
        
        ttl = await self.redis.ttl(window_key)
        reset_time = int(now + ttl)
        
        is_allowed = current <= max_requests
        remaining = max(0, max_requests - current)
        
        return is_allowed, {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_time,
            "retry_after": ttl if not is_allowed else 0,
        }
    
    async def _token_bucket(
        self,
        key: str,
        max_tokens: int,
        refill_seconds: int,
    ) -> tuple[bool, dict]:
        """Token bucket rate limiting (allows bursting)."""
        
        now = time.time()
        refill_rate = max_tokens / refill_seconds
        
        # Get current bucket state
        bucket = await self.redis.hgetall(key)
        
        if not bucket:
            tokens = max_tokens - 1
            last_update = now
        else:
            tokens = float(bucket.get("tokens", max_tokens))
            last_update = float(bucket.get("last_update", now))
            
            # Refill tokens
            elapsed = now - last_update
            tokens = min(max_tokens, tokens + elapsed * refill_rate)
        
        is_allowed = tokens >= 1
        
        if is_allowed:
            tokens -= 1
        
        # Update bucket
        await self.redis.hset(key, mapping={
            "tokens": tokens,
            "last_update": now,
        })
        await self.redis.expire(key, refill_seconds * 2)
        
        return is_allowed, {
            "limit": max_tokens,
            "remaining": int(tokens),
            "reset": int(now + (max_tokens - tokens) / refill_rate),
        }


# Rate limit configurations per endpoint type
RATE_LIMITS = {
    # Authentication endpoints - strict limits
    "auth:login": {"max_requests": 5, "window_seconds": 60},
    "auth:refresh": {"max_requests": 20, "window_seconds": 60},
    "auth:register": {"max_requests": 3, "window_seconds": 3600},
    
    # API endpoints - moderate limits
    "api:read": {"max_requests": 100, "window_seconds": 60},
    "api:write": {"max_requests": 30, "window_seconds": 60},
    
    # Session operations - conservative limits
    "session:create": {"max_requests": 10, "window_seconds": 60},
    "session:execute": {"max_requests": 20, "window_seconds": 60},
    
    # LLM endpoints - expensive, strict limits
    "llm:configure": {"max_requests": 10, "window_seconds": 60},
    "llm:test": {"max_requests": 5, "window_seconds": 60},
    
    # WebSocket connections
    "websocket:connect": {"max_requests": 10, "window_seconds": 60},
    
    # Global limits (fallback)
    "global": {"max_requests": 500, "window_seconds": 60},
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        get_user_id: Optional[Callable] = None,
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.get_user_id = get_user_id
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/status"]:
            return await call_next(request)
        
        # Determine rate limit key
        key = await self._get_rate_limit_key(request)
        
        # Determine rate limit config
        config = self._get_rate_limit_config(request)
        
        # Check rate limit
        is_allowed, metadata = await self.rate_limiter.is_allowed(
            key=key,
            max_requests=config["max_requests"],
            window_seconds=config["window_seconds"],
        )
        
        # Add rate limit headers
        response = await call_next(request) if is_allowed else None
        
        if not is_allowed:
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests",
                    "retry_after": metadata["retry_after"],
                },
                headers={
                    "X-RateLimit-Limit": str(metadata["limit"]),
                    "X-RateLimit-Remaining": str(metadata["remaining"]),
                    "X-RateLimit-Reset": str(metadata["reset"]),
                    "Retry-After": str(metadata["retry_after"]),
                },
            )
        
        # Add rate limit headers to response
        if response:
            response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
            response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
            response.headers["X-RateLimit-Reset"] = str(metadata["reset"])
        
        return response
    
    async def _get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key based on IP and/or user."""
        
        # Get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        # Get user ID if authenticated
        user_id = None
        if self.get_user_id:
            user_id = await self.get_user_id(request)
        
        # Create key
        if user_id:
            return f"ratelimit:user:{user_id}:{request.url.path}"
        else:
            return f"ratelimit:ip:{ip}:{request.url.path}"
    
    def _get_rate_limit_config(self, request: Request) -> dict:
        """Get rate limit config for the current endpoint."""
        
        path = request.url.path
        method = request.method
        
        # Match endpoint patterns
        if "/auth/login" in path or "/auth/token" in path:
            return RATE_LIMITS["auth:login"]
        elif "/auth/refresh" in path:
            return RATE_LIMITS["auth:refresh"]
        elif "/sessions" in path and method == "POST":
            return RATE_LIMITS["session:create"]
        elif "/sessions" in path and method in ["POST", "PUT", "DELETE"]:
            return RATE_LIMITS["session:execute"]
        elif "/llm/endpoints" in path:
            return RATE_LIMITS["llm:configure"]
        elif "/llm/test" in path:
            return RATE_LIMITS["llm:test"]
        elif method == "GET":
            return RATE_LIMITS["api:read"]
        else:
            return RATE_LIMITS["api:write"]
```

---

## 6. Secure Configuration

### 6.1 Environment Configuration

```python
# src/purple_team_gpt/security/config.py

from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    """Security-related configuration."""
    
    model_config = SettingsConfigDict(env_prefix="SECURITY_")
    
    # JWT Configuration
    jwt_private_key: Optional[str] = None
    jwt_public_key: Optional[str] = None
    jwt_issuer: str = "purple-team-gpt"
    jwt_audience: str = "purple-team-gpt-api"
    jwt_algorithm: str = "RS256"
    access_token_ttl: int = 900  # 15 minutes
    refresh_token_ttl: int = 604800  # 7 days
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_strategy: str = "sliding_window"
    redis_url: str = "redis://localhost:6379/0"
    
    # CORS
    cors_allowed_origins: List[str] = Field(default_factory=lambda: [
        "http://localhost:5173",
        "http://localhost:3000",
    ])
    cors_allow_credentials: bool = True
    cors_max_age: int = 600
    
    # Password Policy
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True
    password_bcrypt_rounds: int = 12
    
    # Session Security
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "strict"
    
    # Input Validation
    max_request_size: int = 10 * 1024 * 1024  # 10 MB
    max_target_length: int = 500
    max_command_length: int = 10000
    
    # SSRF Protection
    ssrf_allow_private_ips: bool = False
    ssrf_allowed_hosts: List[str] = Field(default_factory=list)
    
    # Audit Logging
    audit_enabled: bool = True
    audit_log_requests: bool = True
    audit_log_responses: bool = False
    audit_sensitive_fields: List[str] = Field(default_factory=lambda: [
        "password", "api_key", "secret", "token",
    ])
    
    @field_validator("jwt_private_key", "jwt_public_key")
    @classmethod
    def validate_keys(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("-----BEGIN"):
            raise ValueError("JWT keys must be in PEM format")
        return v
    
    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_origins(cls, v: List[str]) -> List[str]:
        for origin in v:
            if origin == "*":
                raise ValueError(
                    "Wildcard CORS origin is not allowed in production. "
                    "Specify explicit origins."
                )
        return v
```

---

## 7. Security Headers

### 7.1 Security Headers Middleware

```python
# src/purple_team_gpt/security/headers.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS Protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Adjust for your frontend
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=()"
        )
        
        # HSTS (if using HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response
```

---

## 8. Audit Logging

### 8.1 Audit Logger

```python
# src/purple_team_gpt/security/audit.py

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from fastapi import Request


class AuditEventType(str, Enum):
    """Types of audit events."""
    
    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"
    TOKEN_REVOKED = "auth.token.revoked"
    
    # Authorization events
    ACCESS_GRANTED = "auth.access.granted"
    ACCESS_DENIED = "auth.access.denied"
    
    # Session events
    SESSION_CREATE = "session.create"
    SESSION_START = "session.start"
    SESSION_STOP = "session.stop"
    SESSION_DELETE = "session.delete"
    
    # LLM events
    LLM_ENDPOINT_ADD = "llm.endpoint.add"
    LLM_ENDPOINT_REMOVE = "llm.endpoint.remove"
    LLM_CONFIG_CHANGE = "llm.config.change"
    
    # Tool events
    TOOL_EXECUTE = "tool.execute"
    TOOL_INSTALL = "tool.install"
    
    # Admin events
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    ROLE_ASSIGN = "role.assign"
    
    # Security events
    RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    INVALID_TOKEN = "security.token.invalid"
    SUSPICIOUS_ACTIVITY = "security.suspicious"


class AuditLogger:
    """Structured audit logger for security events."""
    
    def __init__(
        self,
        logger: logging.Logger,
        sensitive_fields: set,
        mask_sensitive: bool = True,
    ):
        self.logger = logger
        self.sensitive_fields = sensitive_fields
        self.mask_sensitive = mask_sensitive
    
    def log(
        self,
        event_type: AuditEventType,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ):
        """Log an audit event."""
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "success": success,
            "user_id": user_id,
            "org_id": org_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": self._mask_sensitive(details) if details else None,
        }
        
        if request:
            event["request"] = {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
            }
        
        # Log as JSON for structured logging
        self.logger.info(json.dumps(event))
    
    def _mask_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in audit logs."""
        if not self.mask_sensitive:
            return data
        
        result = {}
        for key, value in data.items():
            if key.lower() in self.sensitive_fields:
                result[key] = "***MASKED***"
            elif isinstance(value, dict):
                result[key] = self._mask_sensitive(value)
            else:
                result[key] = value
        return result
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# Decorator for auditing endpoint access
def audit_endpoint(
    event_type: AuditEventType,
    resource_type: Optional[str] = None,
):
    """Decorator to audit endpoint access."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            auth_context = None
            
            # Extract request and auth context from args/kwargs
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, AuthContext):
                    auth_context = arg
            
            # Execute the function
            try:
                result = await func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                # Log the audit event
                audit_logger: AuditLogger = request.app.state.audit_logger if request else None
                if audit_logger:
                    audit_logger.log(
                        event_type=event_type,
                        request=request,
                        user_id=auth_context.user_id if auth_context else None,
                        org_id=auth_context.org_id if auth_context else None,
                        resource_type=resource_type,
                        success=success,
                    )
            
            return result
        
        return wrapper
    return decorator
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Implement JWT authentication system
- [ ] Add security settings configuration
- [ ] Create user database schema
- [ ] Implement password hashing

### Phase 2: Middleware (Week 2-3)
- [ ] Add JWT authentication middleware
- [ ] Implement authorization middleware
- [ ] Add rate limiting middleware
- [ ] Add security headers middleware

### Phase 3: Input Validation (Week 3-4)
- [ ] Implement input validation layer
- [ ] Add SSRF protection for LLM endpoints
- [ ] Add command validation for tool execution
- [ ] Add target validation with scope checks

### Phase 4: Audit & Monitoring (Week 4-5)
- [ ] Implement audit logging
- [ ] Add security event monitoring
- [ ] Create audit dashboard
- [ ] Set up alerting for suspicious activity

### Phase 5: WebSocket Security (Week 5-6)
- [ ] Add WebSocket authentication
- [ ] Implement connection rate limiting
- [ ] Add message validation
- [ ] Session management for WebSocket

---

## 10. Security Checklist

### Authentication
- [ ] JWT tokens signed with RS256
- [ ] Short-lived access tokens (15 min)
- [ ] Refresh token rotation
- [ ] Token revocation support
- [ ] Secure token storage on client

### Authorization
- [ ] Role-based access control
- [ ] Resource-level authorization
- [ ] Permission checks on all endpoints
- [ ] Principle of least privilege

### Input Validation
- [ ] All inputs validated with Pydantic
- [ ] SSRF protection for URLs
- [ ] Command injection prevention
- [ ] Target scope validation

### Rate Limiting
- [ ] Redis-backed rate limiting
- [ ] Per-user and per-IP limits
- [ ] Rate limit headers in responses
- [ ] 429 responses with Retry-After

### CORS
- [ ] Explicit origin list (no wildcards)
- [ ] Credentials allowed only for specific origins
- [ ] Limited allowed headers
- [ ] Max-age configured

### Headers
- [ ] X-Frame-Options: DENY
- [ ] X-Content-Type-Options: nosniff
- [ ] Content-Security-Policy
- [ ] Strict-Transport-Security (HTTPS)

### Audit
- [ ] All security events logged
- [ ] Sensitive data masked
- [ ] Structured JSON logging
- [ ] Audit trail immutable