"""Authentication and authorization for distributed Purple Team GPT.

This module provides authentication mechanisms for securing
communication between orchestrator and agent services.
"""

import hashlib
import hmac
import secrets
import time
from typing import Dict, Optional

from pydantic import BaseModel


class AgentCredentials(BaseModel):
    """Credentials for an agent."""
    agent_id: str
    api_key: str
    agent_type: str
    roles: list[str] = ["agent"]
    created_at: float = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.created_at:
            self.created_at = time.time()


class AuthManager:
    """Manages authentication for distributed agents.
    
    Provides:
    - API key generation and validation
    - Request signing for message integrity
    - Agent registration management
    
    Example:
        auth = AuthManager("my-secret-key")
        api_key = auth.register_agent("agent-1", "red")
        
        # Verify request
        if auth.verify_api_key(api_key):
            # Valid agent
            pass
    """
    
    def __init__(self, secret_key: str):
        """Initialize auth manager.
        
        Args:
            secret_key: Master secret for signing operations
        """
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self._registered_agents: Dict[str, AgentCredentials] = {}
        self._api_keys: Dict[str, str] = {}  # api_key -> agent_id
    
    def generate_api_key(self) -> str:
        """Generate a secure API key.
        
        Returns:
            32-byte URL-safe API key
        """
        return secrets.token_urlsafe(32)
    
    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        roles: Optional[list] = None,
    ) -> str:
        """Register an agent and return its API key.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (red/blue)
            roles: Optional list of roles
            
        Returns:
            API key for the agent
        """
        # Revoke existing registration if any
        if agent_id in self._registered_agents:
            old_key = self._registered_agents[agent_id].api_key
            self._api_keys.pop(old_key, None)
        
        # Generate new API key
        api_key = self.generate_api_key()
        
        # Store credentials
        self._registered_agents[agent_id] = AgentCredentials(
            agent_id=agent_id,
            api_key=api_key,
            agent_type=agent_type,
            roles=roles or ["agent"],
        )
        self._api_keys[api_key] = agent_id
        
        return api_key
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent.
        
        Args:
            agent_id: Agent to unregister
            
        Returns:
            True if agent was unregistered
        """
        if agent_id in self._registered_agents:
            api_key = self._registered_agents[agent_id].api_key
            del self._registered_agents[agent_id]
            self._api_keys.pop(api_key, None)
            return True
        return False
    
    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return agent_id.
        
        Args:
            api_key: API key to verify
            
        Returns:
            Agent ID if valid, None otherwise
        """
        return self._api_keys.get(api_key)
    
    def get_agent(self, agent_id: str) -> Optional[AgentCredentials]:
        """Get agent credentials by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent credentials or None
        """
        return self._registered_agents.get(agent_id)
    
    def get_agent_by_key(self, api_key: str) -> Optional[AgentCredentials]:
        """Get agent credentials by API key.
        
        Args:
            api_key: API key
            
        Returns:
            Agent credentials or None
        """
        agent_id = self._api_keys.get(api_key)
        if agent_id:
            return self._registered_agents.get(agent_id)
        return None
    
    def sign_request(
        self,
        api_key: str,
        timestamp: str,
        payload: str,
    ) -> str:
        """Create request signature.
        
        Args:
            api_key: Agent's API key
            timestamp: Request timestamp (ISO format)
            payload: Request payload (JSON string)
            
        Returns:
            HMAC signature
        """
        message = f"{api_key}:{timestamp}:{payload}".encode()
        return hmac.new(
            self.secret_key,
            message,
            hashlib.sha256
        ).hexdigest()
    
    def verify_signature(
        self,
        api_key: str,
        timestamp: str,
        signature: str,
        payload: str,
        max_age_seconds: int = 300,
    ) -> bool:
        """Verify request signature.
        
        Args:
            api_key: Agent's API key
            timestamp: Request timestamp
            signature: Provided signature
            payload: Request payload
            max_age_seconds: Maximum age for replay protection
            
        Returns:
            True if signature is valid
        """
        # Check API key
        if api_key not in self._api_keys:
            return False
        
        # Check timestamp (replay protection)
        try:
            ts = float(timestamp)
            if abs(time.time() - ts) > max_age_seconds:
                return False
        except (ValueError, TypeError):
            return False
        
        # Verify signature
        expected = self.sign_request(api_key, timestamp, payload)
        return secrets.compare_digest(signature, expected)
    
    def list_agents(self) -> list[AgentCredentials]:
        """List all registered agents.
        
        Returns:
            List of agent credentials
        """
        return list(self._registered_agents.values())
    
    def generate_token(self, agent_id: str, expires_in: int = 3600) -> str:
        """Generate a time-limited token for an agent.
        
        Args:
            agent_id: Agent identifier
            expires_in: Token validity in seconds
            
        Returns:
            Time-limited token
        """
        if agent_id not in self._registered_agents:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        agent = self._registered_agents[agent_id]
        expiry = int(time.time()) + expires_in
        data = f"{agent_id}:{agent.api_key}:{expiry}"
        
        signature = hmac.new(
            self.secret_key,
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{agent_id}:{expiry}:{signature}"
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify a time-limited token.
        
        Args:
            token: Token to verify
            
        Returns:
            Agent ID if valid, None otherwise
        """
        try:
            parts = token.split(":")
            if len(parts) != 3:
                return None
            
            agent_id, expiry_str, signature = parts
            expiry = int(expiry_str)
            
            # Check expiry
            if time.time() > expiry:
                return None
            
            # Check agent exists
            if agent_id not in self._registered_agents:
                return None
            
            agent = self._registered_agents[agent_id]
            
            # Verify signature
            data = f"{agent_id}:{agent.api_key}:{expiry}"
            expected_sig = hmac.new(
                self.secret_key,
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if secrets.compare_digest(signature, expected_sig):
                return agent_id
            
        except (ValueError, TypeError):
            pass
        
        return None