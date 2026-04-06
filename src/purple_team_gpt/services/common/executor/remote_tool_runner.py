"""Remote Tool Runner for distributed agent services.

This module provides the tool execution framework for agents
running on remote systems with direct access to security tools.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    duration_ms: float = 0
    tool_name: str = ""
    command: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "return_code": self.return_code,
            "duration_ms": self.duration_ms,
            "tool_name": self.tool_name,
            "command": self.command,
            "timestamp": self.timestamp.isoformat(),
        }


class RemoteToolRunner:
    """Executes security tools locally on the agent's host system.
    
    Designed for distributed deployment where the agent has direct
    access to security tools and target networks.
    
    Features:
    - Command validation and sanitization
    - Timeout enforcement
    - Execution logging
    - Safe mode for blocking dangerous operations
    
    Example:
        runner = RemoteToolRunner(agent_type="red", safe_mode=True)
        result = await runner.execute("nmap", "nmap -sV target.com")
        print(result.output)
    """
    
    # Tool definitions by agent type
    RED_TOOLS = {
        # Network scanning
        "nmap", "masscan", "zmap",
        # Web scanning
        "nikto", "whatweb", "wpscan", "dirb", "gobuster", "ffuf",
        # Vulnerability testing
        "sqlmap", "nuclei", "wpscan",
        # Exploitation
        "searchsploit", "metasploit",
        # Credentials
        "hydra", "ncrack", "john", "hashcat",
        # Network utilities
        "curl", "wget", "dig", "nslookup", "whois",
        # Enumeration
        "enum4linux", "smbclient", "rpcclient", "ldapsearch",
        # Custom scripts
        "python3", "bash",
    }
    
    BLUE_TOOLS = {
        # System monitoring
        "ps", "top", "htop", "lsof", "ss", "netstat",
        # Log analysis
        "journalctl", "log_analyzer", "grep", "awk", "tail",
        # File integrity
        "aide", "tripwire", "file_integrity",
        # Firewall
        "iptables", "ufw", "firewall-cmd", "nft",
        # Service management
        "systemctl", "service",
        # User management
        "last", "who", "w", "lastlog",
        # Security tools
        "rkhunter", "chkrootkit", "clamav", "freshclam",
        # Audit
        "auditctl", "ausearch", "aureport",
    }
    
    # Dangerous patterns to block
    DESTRUCTIVE_PATTERNS = [
        "rm -rf /",
        "rm -rf /*",
        "dd if=/dev/zero",
        "dd if=/dev/urandom",
        "mkfs",
        ":(){ :|:& };:",  # Fork bomb
        "chmod 777 /",
        "chmod -R 777 /",
        "> /dev/sd",
        "shutdown",
        "reboot",
        "init 0",
        "init 6",
        "halt",
        "poweroff",
    ]
    
    # Patterns requiring extra caution
    CAUTION_PATTERNS = [
        "rm ",
        "chmod",
        "chown",
        "kill -9",
        "pkill",
        "killall",
    ]
    
    def __init__(
        self,
        agent_type: str,
        safe_mode: bool = True,
        default_timeout: int = 300,
        allowed_tools: Optional[set] = None,
        on_execute: Optional[Callable[[str, str], None]] = None,
    ):
        """Initialize the tool runner.
        
        Args:
            agent_type: "red" or "blue"
            safe_mode: Enable safe mode (blocks dangerous commands)
            default_timeout: Default timeout in seconds
            allowed_tools: Custom allowed tools set (uses defaults if None)
            on_execute: Callback before each execution
        """
        self.agent_type = agent_type
        self.safe_mode = safe_mode
        self.default_timeout = default_timeout
        self.allowed_tools = allowed_tools or (
            self.RED_TOOLS if agent_type == "red" else self.BLUE_TOOLS
        )
        self.on_execute = on_execute
        self._execution_log: List[Dict[str, Any]] = []
        self._total_executions = 0
        self._failed_executions = 0
    
    def validate_command(self, command: str, tool_name: str) -> tuple[bool, str]:
        """Validate command for safety and compliance.
        
        Args:
            command: Full command string
            tool_name: Name of the tool
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not command:
            return False, "Empty command"
        
        command_lower = command.lower()
        
        # Check for destructive patterns
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if pattern.lower() in command_lower:
                return False, f"Destructive pattern blocked: {pattern}"
        
        # In safe mode, check caution patterns
        if self.safe_mode:
            for pattern in self.CAUTION_PATTERNS:
                if pattern.lower() in command_lower:
                    return False, f"Pattern blocked in safe mode: {pattern}"
        
        # Extract base tool name
        tool_base = tool_name.split()[0] if tool_name else ""
        
        # Check if tool is in allowed list
        if tool_base and tool_base not in self.allowed_tools:
            logger.warning(f"Tool '{tool_base}' not in allowed list, but executing")
        
        return True, ""
    
    async def execute(
        self,
        tool_name: str,
        command: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ToolResult:
        """Execute a tool command.
        
        Args:
            tool_name: Name of the tool
            command: Full command to execute
            timeout: Timeout in seconds (uses default if None)
            env: Additional environment variables
            
        Returns:
            ToolResult with execution details
        """
        start_time = time.time()
        timestamp = datetime.utcnow()
        
        # Validate command
        is_valid, error_msg = self.validate_command(command, tool_name)
        if not is_valid:
            return ToolResult(
                success=False,
                output="",
                error=error_msg,
                tool_name=tool_name,
                command=command,
                duration_ms=0,
                timestamp=timestamp,
            )
        
        # Callback
        if self.on_execute:
            try:
                self.on_execute(tool_name, command)
            except Exception as e:
                logger.warning(f"Execute callback error: {e}")
        
        timeout = timeout or self.default_timeout
        self._total_executions += 1
        
        try:
            # Build environment
            import os
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
            
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=exec_env,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                
                self._failed_executions += 1
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout}s",
                    tool_name=tool_name,
                    command=command,
                    duration_ms=(time.time() - start_time) * 1000,
                    timestamp=timestamp,
                )
            
            duration_ms = (time.time() - start_time) * 1000
            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")
            
            # Combine outputs
            full_output = output
            if error_output and not output:
                full_output = error_output
            elif error_output:
                full_output = f"{output}\n{error_output}"
            
            success = process.returncode == 0
            if not success:
                self._failed_executions += 1
            
            result = ToolResult(
                success=success,
                output=full_output,
                error=error_output if not success else None,
                return_code=process.returncode or 0,
                duration_ms=duration_ms,
                tool_name=tool_name,
                command=command,
                timestamp=timestamp,
            )
            
            # Log execution
            self._execution_log.append({
                "tool": tool_name,
                "command": command[:500],  # Truncate
                "success": success,
                "duration_ms": duration_ms,
                "return_code": result.return_code,
                "timestamp": timestamp.isoformat(),
            })
            
            # Trim log if too large
            if len(self._execution_log) > 1000:
                self._execution_log = self._execution_log[-500:]
            
            return result
            
        except Exception as e:
            self._failed_executions += 1
            return ToolResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                tool_name=tool_name,
                command=command,
                duration_ms=(time.time() - start_time) * 1000,
                timestamp=timestamp,
            )
    
    async def execute_script(
        self,
        script_path: str,
        args: List[str] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """Execute a script file.
        
        Args:
            script_path: Path to the script
            args: Arguments to pass
            timeout: Timeout in seconds
            
        Returns:
            ToolResult
        """
        import os
        
        if not os.path.exists(script_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Script not found: {script_path}",
                tool_name="script",
                command=script_path,
            )
        
        # Determine interpreter
        if script_path.endswith(".py"):
            cmd = f"python3 {script_path}"
        elif script_path.endswith(".sh"):
            cmd = f"bash {script_path}"
        else:
            cmd = script_path
        
        if args:
            cmd += " " + " ".join(args)
        
        return await self.execute(
            tool_name="script",
            command=cmd,
            timeout=timeout,
        )
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get list of all tool executions."""
        return self._execution_log.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        success_rate = 0
        if self._total_executions > 0:
            success_rate = (self._total_executions - self._failed_executions) / self._total_executions * 100
        
        return {
            "agent_type": self.agent_type,
            "safe_mode": self.safe_mode,
            "total_executions": self._total_executions,
            "failed_executions": self._failed_executions,
            "success_rate": round(success_rate, 2),
            "allowed_tools_count": len(self.allowed_tools),
        }
    
    def clear_log(self) -> None:
        """Clear execution log."""
        self._execution_log.clear()
    
    def add_allowed_tool(self, tool_name: str) -> None:
        """Add a tool to the allowed list."""
        self.allowed_tools.add(tool_name)
    
    def remove_allowed_tool(self, tool_name: str) -> None:
        """Remove a tool from the allowed list."""
        self.allowed_tools.discard(tool_name)
    
    async def check_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available on the system.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is available
        """
        result = await self.execute(
            tool_name="which",
            command=f"which {tool_name}",
            timeout=5,
        )
        return result.success


class ToolExecutorPool:
    """Manages multiple tool executors for different purposes.
    
    Useful for:
    - Isolating execution environments
    - Different timeout profiles
    - Agent-specific tool sets
    """
    
    def __init__(self):
        self._executors: Dict[str, RemoteToolRunner] = {}
    
    def get_executor(
        self,
        name: str,
        agent_type: str = "red",
        **kwargs
    ) -> RemoteToolRunner:
        """Get or create an executor.
        
        Args:
            name: Executor name
            agent_type: "red" or "blue"
            **kwargs: Additional arguments for RemoteToolRunner
            
        Returns:
            RemoteToolRunner instance
        """
        if name not in self._executors:
            self._executors[name] = RemoteToolRunner(
                agent_type=agent_type,
                **kwargs
            )
        return self._executors[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats from all executors."""
        return {
            name: executor.get_stats()
            for name, executor in self._executors.items()
        }