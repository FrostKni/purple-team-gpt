"""Red Agent - Offensive Security Testing.

This module implements the Red Agent, an autonomous offensive security testing AI
that performs authorized penetration testing, vulnerability assessment, and
security auditing within defined scope.
"""

import asyncio
import logging
import shlex
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from purple_team_gpt.agents.base import (
    AgentAction,
    AgentRole,
    AgentState,
    AgentStep,
    BaseAgent,
    Finding,
)

logger = logging.getLogger(__name__)


RED_AGENT_PROMPT = """You are the Red Agent, an autonomous offensive security testing AI.

IDENTITY:
You are part of Purple Team GPT, a cybersecurity simulation framework.
Your role is to perform authorized offensive security testing to identify
vulnerabilities before malicious actors can exploit them.

CAPABILITIES:
- Reconnaissance: Port scanning, service enumeration, OS fingerprinting, DNS enumeration
- Vulnerability scanning: Web app scanning, CVE detection, configuration analysis
- Exploitation: SQL injection testing, XSS testing, credential testing
- Post-exploitation: Privilege escalation checks, lateral movement simulation
- Reporting: Detailed findings with evidence and recommendations

AVAILABLE TOOLS:
- nmap: Network/port scanning (nmap -sV -sC target)
- nikto: Web vulnerability scanning (nikto -h target)
- gobuster: Directory brute forcing (gobuster dir -u URL -w wordlist)
- sqlmap: SQL injection testing (sqlmap -u URL --batch)
- curl: HTTP requests (curl -s URL)
- dig: DNS enumeration (dig target)
- whatweb: Web technology fingerprinting (whatweb URL)
- ncrack: Credential testing (ncrack -p 22 target -u user -P pass.txt)
- hydra: Password brute forcing (hydra -l user -P pass.txt target ssh)

METHODOLOGY:
Follow this structured approach:
1. Reconnaissance: Gather information about the target
2. Scanning: Identify open ports, services, and potential vulnerabilities
3. Enumeration: Extract detailed information from discovered services
4. Vulnerability Analysis: Identify and verify security weaknesses
5. Exploitation Testing: Safely test identified vulnerabilities
6. Post-Exploitation: Assess impact and identify additional risks
7. Reporting: Document all findings with evidence

SAFETY RULES:
1. ONLY test targets you have EXPLICIT authorization for
2. Never perform destructive operations without explicit approval
3. Respect rate limits to avoid denial of service
4. Document all actions taken for audit trail
5. Stop immediately if unauthorized access indicators found
6. Use safe_mode to prevent potentially harmful operations

SEVERITY CLASSIFICATIONS:
- Critical: Immediate exploitation possible, severe impact
- High: Significant vulnerability, likely exploitable
- Medium: Moderate risk, requires specific conditions
- Low: Minor issue, limited security impact
- Info: Informational finding, no direct security impact

OUTPUT FORMAT:
To execute a tool, include a JSON action block:
```json
{
  "action": "execute",
  "tool": "nmap",
  "command": "nmap -sV -sC 192.168.1.1",
  "explanation": "Service version detection with default scripts on target"
}
```

To report a security finding:
```json
{
  "action": "finding",
  "title": "Open SSH Port with Weak Configuration",
  "severity": "Medium",
  "description": "SSH service exposed on port 22 with password authentication enabled",
  "evidence": "22/tcp open ssh OpenSSH 7.6p1| password authentication enabled",
  "recommendation": "Disable password authentication, use key-based auth, restrict access via firewall"
}
```

To query for relevant attack patterns from past engagements:
```json
{
  "action": "query_rag",
  "parameters": {"query": "SSH brute force techniques"}
}
```

When assessment is complete:
```json
{
  "action": "complete",
  "explanation": "All authorized tests completed successfully"
}
```

IMPORTANT:
- Always explain your reasoning before each action
- Provide detailed evidence for all findings
- Include specific remediation recommendations
- Learn from patterns stored in RAG memory
- Maintain professional and ethical conduct
"""


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    duration_ms: float = 0


class ToolRunner:
    """Executes security tools safely.
    
    Provides a safe interface for running security tools with:
    - Command validation
    - Timeout enforcement
    - Output capture
    - Error handling
    """
    
    # Allowed tools for execution
    ALLOWED_TOOLS = {
        "nmap", "nikto", "gobuster", "sqlmap", "curl", "dig",
        "whatweb", "ncrack", "hydra", "whois", "nbtscan",
        "enum4linux", "smbclient", "rpcclient", "ldapsearch",
    }
    
    # Tools blocked in safe mode
    DESTRUCTIVE_TOOLS = {
        "dd", "mkfs", "fdisk", "shred", "wipe", "rm",
    }
    
    def __init__(self, safe_mode: bool = True, default_timeout: int = 300):
        """Initialize the tool runner.
        
        Args:
            safe_mode: If True, blocks potentially destructive commands
            default_timeout: Default timeout in seconds
        """
        self.safe_mode = safe_mode
        self.default_timeout = default_timeout
    
    # Path traversal patterns to block
    PATH_TRAVERSAL_PATTERNS = [
        "../",           # Parent directory traversal
        "..\\",          # Windows parent directory traversal
        "/etc/passwd",   # Sensitive file access
        "/etc/shadow",   # Sensitive file access
        "/root/",        # Root directory access
        "/home/",        # Home directory access (when not intended)
        "~",             # Home directory expansion
        "$HOME",         # Environment variable expansion
        "${HOME}",       # Environment variable expansion
        "$USER",         # Environment variable expansion
        "${USER}",       # Environment variable expansion
    ]
    
    def _validate_command(self, command: str, tool_name: str) -> tuple[bool, str]:
        """Validate command for safety.
        
        Args:
            command: The command to validate
            tool_name: Name of the tool
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not command:
            return False, "Empty command"
        
        # Validate the tool binary is in the allowed list
        try:
            args = shlex.split(command)
        except ValueError as e:
            return False, f"Invalid command syntax: {e}"
        
        if not args:
            return False, "Empty command after parsing"
        
        # SECURITY: Ensure the binary path doesn't contain path traversal
        binary_path = args[0]
        tool_binary = binary_path.split("/")[-1]  # basename only
        
        # Block absolute paths that try to access non-standard locations
        if binary_path.startswith("/"):
            # Only allow standard system paths for known tools
            allowed_prefixes = ["/usr/bin/", "/usr/local/bin/", "/bin/"]
            if not any(binary_path.startswith(prefix) for prefix in allowed_prefixes):
                # Check if it's a relative path disguised as absolute
                if ".." in binary_path:
                    return False, "Path traversal detected in tool path"
        
        # Block relative paths with traversal
        if ".." in binary_path or binary_path.startswith("./"):
            return False, "Relative paths with traversal are not allowed"
        
        if tool_binary not in self.ALLOWED_TOOLS:
            return False, f"Tool '{tool_binary}' is not in the allowed tools list"
        
        # Check for path traversal in arguments
        for arg in args[1:]:
            if ".." in arg:
                # Allow .. only in specific safe contexts (like URLs for tools)
                if not any(safe in arg for safe in ["http://", "https://"]):
                    return False, f"Path traversal detected in argument: {arg[:50]}"
            
            # Check for sensitive file access in arguments
            sensitive_patterns = ["/etc/passwd", "/etc/shadow", "/root/", "/home/"]
            for pattern in sensitive_patterns:
                if pattern in arg:
                    return False, f"Sensitive file path detected in argument: {pattern}"
        
        # Check for destructive tools in safe mode
        if self.safe_mode:
            for destructive in self.DESTRUCTIVE_TOOLS:
                if destructive in command.lower():
                    return False, f"Tool '{destructive}' not allowed in safe mode"
        
        # Check for dangerous shell injection patterns
        dangerous_patterns = [
            "rm -rf /",
            "> /dev/sd",
            "mkfs",
            ":(){ :|:& };:",  # Fork bomb
            "chmod 777 /",
            "$((",            # Arithmetic expansion
            "))",            # Close arithmetic (when combined with above)
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command:
                return False, f"Dangerous pattern detected: {pattern}"
        
        # Check for path traversal patterns
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if pattern.lower() in command.lower():
                # Some tools legitimately use these patterns (e.g., curl with URLs)
                # but we should flag for review in safe mode
                if self.safe_mode and not any(safe in command for safe in ["http://", "https://"]):
                    return False, f"Path traversal pattern detected: {pattern}"
        
        # Additional check for URL-based path traversal (e.g., http://example.com/../../etc/passwd)
        for arg in args[1:]:
            if "http://" in arg or "https://" in arg:
                # Check for path traversal in URL path
                if "/.." in arg or "../" in arg:
                    return False, f"Path traversal detected in URL argument"
        
        # Check for shell metacharacters that could lead to injection
        shell_metacharacters = [";", "|", "`", "$(", "${", "&", "&&", "||", "<", ">", ">>", "<<"]
        for meta in shell_metacharacters:
            if meta in command:
                # These are dangerous and should be blocked
                # shlex.split should handle most, but double-check
                return False, f"Shell metacharacter '{meta}' not allowed in command"
        
        return True, ""
    
    async def execute(
        self,
        command: str,
        tool_name: str = "",
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """Execute a command safely.
        
        Args:
            command: The command to execute
            tool_name: Name of the tool for logging
            timeout: Timeout in seconds
            
        Returns:
            ToolResult with output and status
        """
        # Validate command
        is_valid, error_msg = self._validate_command(command, tool_name)
        if not is_valid:
            return ToolResult(
                success=False,
                output="",
                error=error_msg,
                return_code=-1,
            )
        
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        try:
            # Parse command into argument list to avoid shell injection
            try:
                args = shlex.split(command)
            except ValueError as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid command syntax: {e}",
                    return_code=-1,
                )
            
            # Run command without shell to prevent injection
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout}s",
                    return_code=-1,
                    duration_ms=(time.time() - start_time) * 1000,
                )
            
            duration_ms = (time.time() - start_time) * 1000
            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")
            
            # Combine outputs for tools that write to stderr
            full_output = output
            if error_output and not output:
                full_output = error_output
            elif error_output:
                full_output = f"{output}\n{error_output}"
            
            return ToolResult(
                success=process.returncode == 0,
                output=full_output,
                error=error_output if process.returncode != 0 else None,
                return_code=process.returncode or 0,
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                return_code=-1,
                duration_ms=(time.time() - start_time) * 1000,
            )


class RedAgent(BaseAgent):
    """Offensive security testing agent.
    
    The Red Agent performs authorized penetration testing and vulnerability
    assessment following a structured methodology:
    1. Reconnaissance
    2. Scanning
    3. Enumeration
    4. Vulnerability Analysis
    5. Exploitation Testing
    6. Post-Exploitation Assessment
    7. Reporting
    
    All actions are logged and findings are stored for learning.
    """
    
    role = AgentRole.RED
    
    def __init__(
        self,
        engine: "LLMEngine",
        vector_store: "VectorStore",
        on_step=None,
        on_finding=None,
        on_output=None,
        max_steps: int = 50,
        safe_mode: bool = True,
        tool_timeout: int = 300,
    ):
        """Initialize the Red Agent.
        
        Args:
            engine: LLM engine for planning and analysis
            vector_store: Vector store for RAG queries
            on_step: Callback for step events
            on_finding: Callback for finding events
            on_output: Callback for output messages
            max_steps: Maximum steps per session
            safe_mode: Enable safe mode for tool execution
            tool_timeout: Default timeout for tool execution
        """
        super().__init__(
            engine=engine,
            vector_store=vector_store,
            on_step=on_step,
            on_finding=on_finding,
            on_output=on_output,
            max_steps=max_steps,
        )
        self.safe_mode = safe_mode
        self.tool_timeout = tool_timeout
        self._tool_runner: Optional[ToolRunner] = None
    
    @property
    def system_prompt(self) -> str:
        """Return the Red Agent system prompt."""
        return RED_AGENT_PROMPT
    
    @property
    def tool_runner(self) -> ToolRunner:
        """Get or create the tool runner."""
        if self._tool_runner is None:
            self._tool_runner = ToolRunner(
                safe_mode=self.safe_mode,
                default_timeout=self.tool_timeout,
            )
        return self._tool_runner
    
    async def plan(self, context: str) -> List[AgentAction]:
        """Plan offensive actions based on context.
        
        Queries RAG for relevant attack patterns and uses the LLM
        to plan appropriate next actions.
        
        Args:
            context: Current situation description
            
        Returns:
            List of actions to execute
        """
        # Query RAG for similar attack patterns
        rag_context = await self.query_rag(
            f"attack patterns for {self.target} {context[:100]}"
        )
        
        # Build planning prompt
        planning_prompt = f"""Target: {self.target}
Scope: {self.scope or 'Full authorized assessment'}
Safe Mode: {'Enabled' if self.safe_mode else 'Disabled'}

Context from previous engagements:
{rag_context if rag_context else 'No relevant patterns found'}

Current situation:
{context}

Plan your next actions. Consider:
1. What reconnaissance has been completed?
2. What services/ports have been identified?
3. What vulnerabilities might exist based on discovered services?
4. What tools would be most effective for the next phase?
5. Are there any findings that need to be reported?

Provide your plan as JSON action blocks. Explain your reasoning before each action."""

        # Add to conversation and get response
        self.conversation.add_user(planning_prompt)
        response = await self.engine.chat(self.conversation)
        self.conversation.add_assistant(response)
        
        # Parse actions from response
        actions = self._parse_actions(response)
        
        if not actions:
            # If no actions parsed, create a default reconnaissance action
            self.output("No valid actions parsed, defaulting to reconnaissance")
            actions = [AgentAction(
                action_type="execute",
                tool="nmap",
                command=f"nmap -sV -sC {self.target}",
                explanation="Default reconnaissance scan",
            )]
        
        return actions
    
    async def execute_action(self, action: AgentAction) -> str:
        """Execute an offensive action.
        
        Handles different action types:
        - execute: Run a security tool
        - finding: Record a security finding
        - query_rag: Query vector store
        - complete: End assessment
        - wait: Pause for duration
        
        Args:
            action: The action to execute
            
        Returns:
            Result string from the action
        """
        self._step_counter += 1
        start_time = time.time()
        
        try:
            if action.action_type == "execute":
                result = await self._execute_tool(action)
            elif action.action_type == "finding":
                result = await self._record_finding(action)
            elif action.action_type == "query_rag":
                result = await self._query_rag_action(action)
            elif action.action_type == "complete":
                self.state = AgentState.COMPLETED
                result = f"Assessment completed: {action.explanation}"
            elif action.action_type == "wait":
                duration = action.parameters.get("seconds", 5)
                await asyncio.sleep(duration)
                result = f"Waited {duration} seconds"
            else:
                result = f"Unknown action type: {action.action_type}"
                logger.warning(result)
            
            success = True
            error = None
            
        except Exception as e:
            result = f"Action failed: {str(e)}"
            success = False
            error = str(e)
            logger.error(f"Action execution error: {e}")
        
        # Record step
        step = AgentStep(
            step_num=self._step_counter,
            action=action,
            result=result[:5000] if result else None,  # Limit stored result size
            success=success,
            error=error,
            duration_ms=(time.time() - start_time) * 1000,
        )
        self.add_step(step)
        
        return result
    
    async def _execute_tool(self, action: AgentAction) -> str:
        """Execute a security tool.
        
        Args:
            action: Action containing tool and command
            
        Returns:
            Tool output or error message
        """
        tool_name = action.tool or "unknown"
        command = action.command or ""
        
        self.output(f"Executing: {tool_name}")
        if action.explanation:
            self.output(f"Reason: {action.explanation}")
        
        # Execute tool
        result = await self.tool_runner.execute(
            command=command,
            tool_name=tool_name,
            timeout=self.tool_timeout,
        )
        
        # Report result
        if result.success:
            self.output(f"Tool completed successfully ({result.duration_ms:.0f}ms)")
        else:
            self.output(f"Tool failed: {result.error}")
        
        # Store result for learning
        await self.store_interaction(
            content=f"Tool: {tool_name}\nCommand: {command}\nResult: {result.output[:1000]}",
            metadata={
                "tool": tool_name,
                "command": command,
                "target": self.target,
                "success": result.success,
                "duration_ms": result.duration_ms,
            }
        )
        
        return result.output if result.output else result.error or "No output"
    
    async def _record_finding(self, action: AgentAction) -> str:
        """Record a security finding.
        
        Args:
            action: Action containing finding details
            
        Returns:
            Confirmation message
        """
        params = action.parameters
        
        finding = Finding(
            title=params.get("title", "Unknown Finding"),
            severity=params.get("severity", "Info"),
            description=params.get("description", ""),
            evidence=params.get("evidence", ""),
            recommendation=params.get("recommendation", ""),
            tool=action.tool or "",
            cve=params.get("cve"),
            cvss_score=params.get("cvss_score"),
        )
        
        self.add_finding(finding)
        self.output(f"Finding recorded: [{finding.severity}] {finding.title}")
        
        # Store in RAG for future reference
        await self.store_interaction(
            content=f"Finding: {finding.title}\nSeverity: {finding.severity}\nTarget: {self.target}\n{finding.description}\nEvidence: {finding.evidence}",
            metadata={
                "type": "finding",
                "severity": finding.severity,
                "target": self.target,
                "tool": finding.tool,
                "cve": finding.cve,
            }
        )
        
        return f"Recorded finding: {finding.title}"
    
    async def _query_rag_action(self, action: AgentAction) -> str:
        """Execute RAG query action.
        
        Args:
            action: Action containing query parameters
            
        Returns:
            Query results
        """
        query = action.parameters.get("query", "")
        if not query:
            return "No query provided"
        
        result = await self.query_rag(query)
        
        if result:
            self.output(f"RAG returned relevant context")
            return f"RAG Context:\n{result}"
        else:
            return "No relevant context found in knowledge base"
    
    async def run_step(self, context: str = "") -> str:
        """Execute a single step of the assessment.
        
        Plans and executes actions for one step of the assessment cycle.
        
        Args:
            context: Current context/situation
            
        Returns:
            Combined results from all executed actions
        """
        # Check step limit
        if self._step_counter >= self.max_steps:
            self.state = AgentState.COMPLETED
            return f"Maximum steps ({self.max_steps}) reached"
        
        # Check state
        if self.state == AgentState.PAUSED:
            return "Agent is paused"
        
        self.state = AgentState.RUNNING
        
        # Plan actions
        actions = await self.plan(context)
        
        # Execute each action
        results = []
        for action in actions:
            # Check for completion or pause
            if self.state == AgentState.COMPLETED:
                break
            if self.state == AgentState.PAUSED:
                results.append("Agent paused during execution")
                break
            
            result = await self.execute_action(action)
            results.append(result)
            
            # Add result to conversation for context
            self.conversation.add_user(f"[RESULT]\n{result[:2000]}")
        
        return "\n\n".join(results)
    
    async def run_assessment(self, initial_context: str = "") -> Dict[str, Any]:
        """Run a complete assessment until completion or max steps.
        
        Args:
            initial_context: Starting context for the assessment
            
        Returns:
            Assessment summary dictionary
        """
        self.output(f"Starting assessment of {self.target}")
        
        context = initial_context
        iteration = 0
        
        while self.state not in (AgentState.COMPLETED, AgentState.ERROR, AgentState.PAUSED):
            iteration += 1
            
            if self._step_counter >= self.max_steps:
                self.output(f"Maximum steps reached ({self.max_steps})")
                self.state = AgentState.COMPLETED
                break
            
            self.output(f"--- Step {iteration} ---")
            
            # Run one step
            result = await self.run_step(context)
            
            # Use result as context for next step
            context = f"Previous step result:\n{result[:1000]}"
            
            # Small delay between steps
            await asyncio.sleep(0.5)
        
        summary = self.get_summary()
        self.output(f"Assessment complete: {len(self.findings)} findings")
        
        return summary
    
    async def quick_scan(self, scan_type: str = "basic") -> Dict[str, Any]:
        """Perform a quick predefined scan.
        
        Args:
            scan_type: Type of scan (basic, full, web, stealth)
            
        Returns:
            Scan results summary
        """
        scan_commands = {
            "basic": f"nmap -sV {self.target}",
            "full": f"nmap -sV -sC -p- {self.target}",
            "web": f"nikto -h {self.target}",
            "stealth": f"nmap -sS -sV -T2 {self.target}",
        }
        
        command = scan_commands.get(scan_type, scan_commands["basic"])
        
        action = AgentAction(
            action_type="execute",
            tool="nmap" if "nmap" in command else "nikto",
            command=command,
            explanation=f"Quick {scan_type} scan",
        )
        
        result = await self.execute_action(action)
        
        return {
            "scan_type": scan_type,
            "target": self.target,
            "result": result,
            "findings": len(self.findings),
        }


def create_red_agent(
    engine: Optional["LLMEngine"] = None,
    vector_store: Optional["VectorStore"] = None,
    **kwargs
) -> RedAgent:
    """Create a Red Agent instance.
    
    Args:
        engine: LLM engine (created if not provided)
        vector_store: Vector store (created if not provided)
        **kwargs: Additional arguments for RedAgent
        
    Returns:
        Configured RedAgent instance
    """
    if engine is None:
        from purple_team_gpt.core.llm.engine import create_engine
        engine = create_engine()
    
    if vector_store is None:
        from purple_team_gpt.core.rag.vector_store import create_vector_store
        vector_store = create_vector_store()
    
    return RedAgent(engine=engine, vector_store=vector_store, **kwargs)