"""
System Agent - Runs directly on bare metal/VM with full system access.

This is the main agent service that:
- Runs as a systemd service
- Has full access to the system
- Can execute any command
- Auto-installs missing tools
- Communicates with the orchestrator
"""

import asyncio
import json
import logging
import os
import platform
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiohttp
from pydantic import BaseModel

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from purple_team_gpt.services.common.tool_manager import (
    ToolManager,
    ToolStatus,
    check_system_requirements,
)
from purple_team_gpt.services.common.protocol import (
    AgentCommand,
    AgentEvent,
    AgentRegistration,
    AgentStatus,
    CommandType,
    EventType,
)
from purple_team_gpt.services.common.auth import (
    AgentAuthenticator,
    sign_request,
)

logger = logging.getLogger(__name__)


class SystemAgentConfig(BaseModel):
    """Configuration for the system agent."""
    agent_type: str
    agent_id: str
    agent_host: str = "0.0.0.0"
    agent_port: int = 8000
    
    orchestrator_url: str = "http://localhost:8000"
    api_key: str = ""
    secret_key: str = ""
    
    auto_install_tools: bool = True
    update_tools_on_start: bool = False
    tool_timeout: int = 300
    
    safe_mode: bool = True
    max_parallel_tools: int = 3
    allowed_targets: List[str] = []
    
    log_level: str = "INFO"
    log_file: str = "/var/log/purple-team-gpt/agent.log"
    
    class Config:
        env_prefix = "AGENT_"


class SystemAgent:
    """Agent that runs directly on the system with full access."""
    
    def __init__(
        self,
        config: SystemAgentConfig,
        custom_tools: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the system agent.
        
        Args:
            config: Agent configuration
            custom_tools: Additional custom tool definitions
        """
        self.config = config
        self.agent_type = config.agent_type
        self.agent_id = config.agent_id
        
        # Tool manager
        self.tool_manager = ToolManager(
            agent_type=config.agent_type,
            auto_install=config.auto_install_tools,
            update_on_start=config.update_tools_on_start,
            custom_tools=custom_tools,
        )
        
        # Authenticator
        self.authenticator = AgentAuthenticator(
            agent_id=config.agent_id,
            api_key=config.api_key,
            secret_key=config.secret_key,
        )
        
        # State
        self.running = False
        self.registered = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        
        # Task queue
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        # Callbacks
        self._event_callbacks: List[Callable] = []
        
        # System info
        self._system_info: Dict[str, Any] = {}
        
    async def start(self) -> None:
        """Start the agent service."""
        logger.info(f"Starting {self.agent_type} agent: {self.agent_id}")
        
        # Gather system info
        self._system_info = await self._gather_system_info()
        logger.info(f"System: {self._system_info['hostname']} ({self._system_info['os']})")
        
        # Check system requirements
        requirements = await check_system_requirements()
        logger.info(f"System requirements: {requirements}")
        
        if not all(requirements.values()):
            missing = [k for k, v in requirements.items() if not v]
            logger.warning(f"Missing requirements: {missing}")
        
        # Initialize tools
        logger.info("Checking tools...")
        tool_status = await self.tool_manager.check_all_tools()
        
        installed = sum(1 for s, _ in tool_status.values() if s == ToolStatus.INSTALLED)
        total = len(tool_status)
        logger.info(f"Tools: {installed}/{total} installed")
        
        # Install missing tools if auto-install enabled
        if self.config.auto_install_tools:
            missing_tools = [name for name, (status, _) in tool_status.items() 
                           if status != ToolStatus.INSTALLED]
            if missing_tools:
                logger.info(f"Installing missing tools: {missing_tools}")
                results = await self.tool_manager.install_missing_tools()
                for name, (success, msg) in results.items():
                    if success:
                        logger.info(f"✓ {name}: {msg}")
                    else:
                        logger.warning(f"✗ {name}: {msg}")
        
        # Create HTTP session
        self.session = aiohttp.ClientSession(
            headers=self.authenticator.get_headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        )
        
        # Register with orchestrator
        await self._register()
        
        # Start main loops
        self.running = True
        
        # Run tasks concurrently
        await asyncio.gather(
            self._heartbeat_loop(),
            self._task_processor(),
            self._websocket_loop(),
        )
    
    async def stop(self) -> None:
        """Stop the agent service."""
        logger.info("Stopping agent...")
        self.running = False
        
        # Cancel running tasks
        for task_id, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close connections
        if self.websocket:
            await self.websocket.close()
        if self.session:
            await self.session.close()
        
        logger.info("Agent stopped")
    
    async def execute_tool(
        self,
        tool_name: str,
        args: List[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute a tool on the system.
        
        Args:
            tool_name: Name of the tool to execute
            args: Arguments for the tool
            timeout: Execution timeout
            env: Environment variables
            
        Returns:
            Dict with exit_code, stdout, stderr, duration
        """
        # Ensure tool is available
        available, msg = await self.tool_manager.ensure_tool(tool_name)
        if not available:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": msg,
                "duration": 0,
            }
        
        # Get tool info
        tool_info = self.tool_manager.get_tool_info(tool_name)
        if not tool_info:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Unknown tool: {tool_name}",
                "duration": 0,
            }
        
        # Build command
        command = tool_name
        if args:
            command = f"{tool_name} {' '.join(args)}"
        
        # Add sudo if needed
        if tool_info.requires_root:
            command = f"sudo {command}"
        
        timeout = timeout or self.config.tool_timeout
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Executing: {command}")
        
        try:
            # Prepare environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
            
            # Execute
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=exec_env,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Timeout after {timeout}s",
                    "duration": timeout,
                }
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "duration": duration,
            }
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Tool execution error: {e}")
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": duration,
            }
    
    async def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        require_root: bool = False,
    ) -> Dict[str, Any]:
        """Execute an arbitrary shell command.
        
        Args:
            command: Shell command to execute
            timeout: Execution timeout
            require_root: Whether to use sudo
            
        Returns:
            Dict with exit_code, stdout, stderr
        """
        # Safe mode check
        if self.config.safe_mode:
            # Block dangerous commands
            dangerous = ["rm -rf /", "mkfs", "dd if=/dev/zero", ":(){ :|:& };:"]
            for d in dangerous:
                if d in command:
                    return {
                        "exit_code": -1,
                        "stdout": "",
                        "stderr": f"Blocked dangerous command (safe_mode)",
                    }
        
        if require_root and not command.startswith("sudo"):
            command = f"sudo {command}"
        
        timeout = timeout or self.config.tool_timeout
        
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            
            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
            
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Timeout after {timeout}s",
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }
    
    def add_event_callback(self, callback: Callable) -> None:
        """Add a callback for events."""
        self._event_callbacks.append(callback)
    
    async def emit_event(self, event: AgentEvent) -> None:
        """Emit an event to callbacks and orchestrator."""
        for callback in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
        
        # Send to orchestrator via WebSocket
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.send_json(event.dict())
            except Exception as e:
                logger.error(f"Failed to send event: {e}")
    
    # =========================================================================
    # Internal methods
    # =========================================================================
    
    async def _gather_system_info(self) -> Dict[str, Any]:
        """Gather system information."""
        info = {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
        }
        
        # Get memory info
        try:
            with open("/proc/meminfo") as f:
                meminfo = dict(
                    line.split(":", 1)
                    for line in f.read().strip().split("\n")
                )
            info["memory_total"] = int(meminfo.get("MemTotal", "0").split()[0])
            info["memory_available"] = int(meminfo.get("MemAvailable", "0").split()[0])
        except:
            pass
        
        # Get IP addresses
        try:
            result = await self.execute_command(
                "hostname -I",
                timeout=5,
                require_root=False,
            )
            if result["exit_code"] == 0:
                info["ip_addresses"] = result["stdout"].strip().split()
        except:
            pass
        
        return info
    
    async def _register(self) -> bool:
        """Register with the orchestrator."""
        logger.info(f"Registering with orchestrator: {self.config.orchestrator_url}")
        
        registration = AgentRegistration(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            host=self.config.agent_host,
            port=self.config.agent_port,
            capabilities=[
                tool.name for tool in self.tool_manager.list_tools()
                if tool.status == ToolStatus.INSTALLED
            ],
            system_info=self._system_info,
        )
        
        try:
            async with self.session.post(
                f"{self.config.orchestrator_url}/api/v1/agents/register",
                json=registration.dict(),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.registered = True
                    logger.info(f"Registered successfully: {data}")
                    return True
                else:
                    error = await response.text()
                    logger.error(f"Registration failed: {response.status} - {error}")
                    return False
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to orchestrator."""
        while self.running:
            try:
                if self.registered:
                    status = AgentStatus(
                        agent_id=self.agent_id,
                        agent_type=self.agent_type,
                        status="active",
                        tools=self.tool_manager.get_status_report(),
                        running_tasks=len(self._running_tasks),
                    )
                    
                    async with self.session.post(
                        f"{self.config.orchestrator_url}/api/v1/agents/{self.agent_id}/heartbeat",
                        json=status.dict(),
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"Heartbeat failed: {response.status}")
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            await asyncio.sleep(30)
    
    async def _task_processor(self) -> None:
        """Process tasks from the queue."""
        while self.running:
            try:
                # Wait for task
                task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                
                # Execute task
                asyncio.create_task(self._execute_task(task))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Task processor error: {e}")
    
    async def _execute_task(self, command: AgentCommand) -> None:
        """Execute a command from the orchestrator."""
        logger.info(f"Executing command: {command.command_type}")
        
        try:
            if command.command_type == CommandType.EXECUTE_TOOL:
                result = await self.execute_tool(
                    tool_name=command.parameters.get("tool"),
                    args=command.parameters.get("args", []),
                    timeout=command.parameters.get("timeout"),
                )
                
                event = AgentEvent(
                    agent_id=self.agent_id,
                    session_id=command.session_id,
                    event_type=EventType.TOOL_RESULT,
                    data=result,
                )
                await self.emit_event(event)
                
            elif command.command_type == CommandType.EXECUTE_COMMAND:
                result = await self.execute_command(
                    command=command.parameters.get("command"),
                    timeout=command.parameters.get("timeout"),
                    require_root=command.parameters.get("require_root", False),
                )
                
                event = AgentEvent(
                    agent_id=self.agent_id,
                    session_id=command.session_id,
                    event_type=EventType.COMMAND_RESULT,
                    data=result,
                )
                await self.emit_event(event)
                
            elif command.command_type == CommandType.INSTALL_TOOL:
                success, msg = await self.tool_manager.install_tool(
                    command.parameters.get("tool")
                )
                
                event = AgentEvent(
                    agent_id=self.agent_id,
                    session_id=command.session_id,
                    event_type=EventType.TOOL_INSTALLED if success else EventType.ERROR,
                    data={"success": success, "message": msg},
                )
                await self.emit_event(event)
                
            elif command.command_type == CommandType.STOP:
                await self.stop()
                
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            event = AgentEvent(
                agent_id=self.agent_id,
                session_id=command.session_id,
                event_type=EventType.ERROR,
                data={"error": str(e)},
            )
            await self.emit_event(event)
    
    async def _websocket_loop(self) -> None:
        """Maintain WebSocket connection to orchestrator."""
        ws_url = self.config.orchestrator_url.replace("http", "ws")
        ws_url = f"{ws_url}/ws/agent/{self.agent_id}"
        
        while self.running:
            try:
                logger.info(f"Connecting to WebSocket: {ws_url}")
                
                async with self.session.ws_connect(ws_url) as ws:
                    self.websocket = ws
                    logger.info("WebSocket connected")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            command = AgentCommand(**data)
                            await self._task_queue.put(command)
                            
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error: {ws.exception()}")
                            break
                            
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.info("WebSocket closed")
                            break
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            self.websocket = None
            
            # Reconnect delay
            if self.running:
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)


# =============================================================================
# Main entry point
# =============================================================================

def load_config(config_path: Optional[str] = None) -> SystemAgentConfig:
    """Load configuration from file or environment."""
    config_data = {}
    
    # Load from file if provided
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            import yaml
            with open(config_file) as f:
                config_data = yaml.safe_load(f) or {}
    
    # Override with environment variables
    env_mappings = {
        "AGENT_TYPE": "agent_type",
        "AGENT_ID": "agent_id",
        "AGENT_HOST": "agent_host",
        "AGENT_PORT": "agent_port",
        "ORCHESTRATOR_URL": "orchestrator_url",
        "AGENT_API_KEY": "api_key",
        "SECRET_KEY": "secret_key",
        "AUTO_INSTALL_TOOLS": ("auto_install_tools", bool),
        "UPDATE_TOOLS_ON_START": ("update_tools_on_start", bool),
        "TOOL_TIMEOUT": ("tool_timeout", int),
        "SAFE_MODE": ("safe_mode", bool),
        "LOG_LEVEL": "log_level",
    }
    
    for env_key, config_key in env_mappings.items():
        value = os.environ.get(env_key)
        if value:
            if isinstance(config_key, tuple):
                key, type_fn = config_key
                if type_fn == bool:
                    config_data[key] = value.lower() in ("true", "1", "yes")
                else:
                    config_data[key] = type_fn(value)
            else:
                config_data[config_key] = value
    
    return SystemAgentConfig(**config_data)


def setup_logging(config: SystemAgentConfig) -> None:
    """Setup logging."""
    log_file = Path(config.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(config.log_file),
            logging.StreamHandler(),
        ],
    )


async def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Purple Team GPT System Agent")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--type", "-t", choices=["red", "blue"], help="Agent type")
    parser.add_argument("--id", "-i", help="Agent ID")
    parser.add_argument("--orchestrator", "-o", help="Orchestrator URL")
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Override with command line args
    if args.type:
        config.agent_type = args.type
    if args.id:
        config.agent_id = args.id
    if args.orchestrator:
        config.orchestrator_url = args.orchestrator
    
    # Setup logging
    setup_logging(config)
    
    # Create and start agent
    agent = SystemAgent(config)
    
    # Handle signals
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(agent.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        pass
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())