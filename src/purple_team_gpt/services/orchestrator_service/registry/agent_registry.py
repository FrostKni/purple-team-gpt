"""Agent Registry for distributed Purple Team GPT.

Manages agent discovery, registration, health monitoring,
and connection pooling for distributed agent services.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable

import aiohttp

from .protocol import AgentInfo, AgentRegistration, AgentStatus, AgentRole

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing distributed agents.
    
    Provides:
    - Agent registration and discovery
    - Health monitoring via heartbeats
    - Agent selection for sessions
    - Connection management
    
    Example:
        registry = AgentRegistry()
        await registry.register(AgentRegistration(...))
        red_agent = registry.select_agent(AgentRole.RED)
    """
    
    def __init__(
        self,
        heartbeat_timeout: int = 60,
        health_check_interval: int = 30,
    ):
        """Initialize the registry.
        
        Args:
            heartbeat_timeout: Seconds before agent marked offline
            health_check_interval: Seconds between health checks
        """
        self.heartbeat_timeout = heartbeat_timeout
        self.health_check_interval = health_check_interval
        
        self._agents: Dict[str, AgentInfo] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._health_task: Optional[asyncio.Task] = None
        self._on_agent_online: Optional[Callable[[str], None]] = None
        self._on_agent_offline: Optional[Callable[[str], None]] = None
    
    async def start(self):
        """Start health monitoring."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        if self._health_task is None:
            self._health_task = asyncio.create_task(self._health_monitor_loop())
    
    async def stop(self):
        """Stop health monitoring."""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None
        
        if self._session:
            await self._session.close()
            self._session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def register(self, registration: AgentRegistration) -> AgentInfo:
        """Register a new agent.
        
        Args:
            registration: Agent registration details
            
        Returns:
            AgentInfo for the registered agent
        """
        url = f"http://{registration.host}:{registration.port}"
        
        agent_info = AgentInfo(
            agent_id=registration.agent_id,
            agent_type=registration.agent_type,
            host=registration.host,
            port=registration.port,
            url=url,
            capabilities=registration.capabilities,
            status=AgentStatus.IDLE,
            last_heartbeat=datetime.utcnow(),
            metadata=registration.metadata,
        )
        
        self._agents[registration.agent_id] = agent_info
        logger.info(f"Registered agent: {registration.agent_id} ({registration.agent_type}) at {url}")
        
        if self._on_agent_online:
            try:
                self._on_agent_online(registration.agent_id)
            except Exception as e:
                logger.warning(f"Online callback error: {e}")
        
        return agent_info
    
    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent.
        
        Args:
            agent_id: Agent to unregister
            
        Returns:
            True if agent was unregistered
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentInfo or None
        """
        return self._agents.get(agent_id)
    
    def list_agents(
        self,
        agent_type: Optional[AgentRole] = None,
        status: Optional[AgentStatus] = None,
    ) -> List[AgentInfo]:
        """List registered agents.
        
        Args:
            agent_type: Filter by agent type
            status: Filter by status
            
        Returns:
            List of matching agents
        """
        agents = list(self._agents.values())
        
        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        
        if status:
            agents = [a for a in agents if a.status == status]
        
        return agents
    
    def select_agent(
        self,
        agent_type: AgentRole,
        exclude: Optional[List[str]] = None,
        prefer_idle: bool = True,
    ) -> Optional[AgentInfo]:
        """Select an agent for a session.
        
        Args:
            agent_type: Type of agent needed
            exclude: Agent IDs to exclude
            prefer_idle: Prefer idle agents over busy ones
            
        Returns:
            Selected AgentInfo or None
        """
        agents = self.list_agents(agent_type=agent_type)
        
        # Filter out excluded and offline agents
        exclude = exclude or []
        agents = [
            a for a in agents
            if a.agent_id not in exclude and a.status != AgentStatus.OFFLINE
        ]
        
        if not agents:
            return None
        
        if prefer_idle:
            # Prefer idle agents
            idle_agents = [a for a in agents if a.status == AgentStatus.IDLE]
            if idle_agents:
                return idle_agents[0]
        
        # Return first available
        return agents[0]
    
    async def heartbeat(self, agent_id: str) -> bool:
        """Process a heartbeat from an agent.
        
        Args:
            agent_id: Agent sending heartbeat
            
        Returns:
            True if heartbeat was processed
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        old_status = agent.status
        agent.last_heartbeat = datetime.utcnow()
        
        # If agent was offline, mark as available
        if agent.status == AgentStatus.OFFLINE:
            agent.status = AgentStatus.IDLE
            logger.info(f"Agent {agent_id} back online")
            
            if self._on_agent_online:
                try:
                    self._on_agent_online(agent_id)
                except Exception as e:
                    logger.warning(f"Online callback error: {e}")
        
        return True
    
    async def send_command(
        self,
        agent_id: str,
        command: Dict[str, Any],
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """Send a command to an agent.
        
        Args:
            agent_id: Target agent
            command: Command to send
            timeout: Request timeout
            
        Returns:
            Response dict or None
        """
        agent = self._agents.get(agent_id)
        if not agent:
            logger.warning(f"Unknown agent: {agent_id}")
            return None
        
        session = await self._get_session()
        url = f"{agent.url}/api/v1/command"
        
        try:
            async with session.post(
                url,
                json=command,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Agent {agent_id} returned {response.status}")
                    return None
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending command to {agent_id}")
            return None
        
        except aiohttp.ClientError as e:
            logger.error(f"Failed to reach agent {agent_id}: {e}")
            return None
    
    async def check_health(self, agent_id: str) -> bool:
        """Check if an agent is healthy.
        
        Args:
            agent_id: Agent to check
            
        Returns:
            True if healthy
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        session = await self._get_session()
        url = f"{agent.url}/api/v1/status"
        
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Update status from response
                    if "status" in data:
                        agent.status = AgentStatus(data.get("status"))
                    return True
                return False
        
        except Exception as e:
            logger.debug(f"Health check failed for {agent_id}: {e}")
            return False
    
    async def _health_monitor_loop(self):
        """Background task to monitor agent health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_agents()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    async def _check_all_agents(self):
        """Check health of all registered agents."""
        now = datetime.utcnow()
        timeout_delta = timedelta(seconds=self.heartbeat_timeout)
        
        for agent_id, agent in list(self._agents.items()):
            # Check heartbeat timeout
            if agent.last_heartbeat:
                if now - agent.last_heartbeat > timeout_delta:
                    if agent.status != AgentStatus.OFFLINE:
                        old_status = agent.status
                        agent.status = AgentStatus.OFFLINE
                        logger.warning(f"Agent {agent_id} marked offline (heartbeat timeout)")
                        
                        if self._on_agent_offline:
                            try:
                                self._on_agent_offline(agent_id)
                            except Exception as e:
                                logger.warning(f"Offline callback error: {e}")
                    continue
            
            # Active health check for non-offline agents
            if agent.status != AgentStatus.OFFLINE:
                healthy = await self.check_health(agent_id)
                if not healthy:
                    logger.warning(f"Agent {agent_id} failed health check")
    
    def set_callbacks(
        self,
        on_online: Optional[Callable[[str], None]] = None,
        on_offline: Optional[Callable[[str], None]] = None,
    ):
        """Set callbacks for agent status changes.
        
        Args:
            on_online: Called when agent comes online
            on_offline: Called when agent goes offline
        """
        self._on_agent_online = on_online
        self._on_agent_offline = on_offline
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        status_counts = {}
        type_counts = {}
        
        for agent in self._agents.values():
            status_counts[agent.status] = status_counts.get(agent.status, 0) + 1
            type_counts[agent.agent_type] = type_counts.get(agent.agent_type, 0) + 1
        
        return {
            "total_agents": len(self._agents),
            "by_status": status_counts,
            "by_type": type_counts,
        }


class ConnectionPool:
    """Manages WebSocket connections to agents.
    
    Maintains persistent connections for real-time
    event streaming from agents.
    """
    
    def __init__(self, max_connections: int = 100):
        """Initialize connection pool.
        
        Args:
            max_connections: Maximum connections to maintain
        """
        self.max_connections = max_connections
        self._connections: Dict[str, Any] = {}  # agent_id -> websocket
    
    async def connect(self, agent_id: str, url: str) -> bool:
        """Establish connection to an agent.
        
        Args:
            agent_id: Agent to connect to
            url: WebSocket URL
            
        Returns:
            True if connected
        """
        # Implementation would use websockets library
        # Placeholder for now
        logger.info(f"Connecting to agent {agent_id} at {url}")
        return True
    
    async def disconnect(self, agent_id: str):
        """Disconnect from an agent."""
        if agent_id in self._connections:
            # Close connection
            del self._connections[agent_id]
            logger.info(f"Disconnected from agent {agent_id}")
    
    async def broadcast(self, message: Dict[str, Any], agent_ids: Optional[List[str]] = None):
        """Broadcast message to agents.
        
        Args:
            message: Message to send
            agent_ids: Specific agents (all if None)
        """
        targets = agent_ids or list(self._connections.keys())
        for agent_id in targets:
            if agent_id in self._connections:
                # Send message
                pass
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)