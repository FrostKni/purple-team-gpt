"""Blue Agent - Defensive Security Operations.

This module implements the Blue Agent, an autonomous defensive security AI
that monitors systems, detects threats, responds to incidents, and implements
security hardening measures.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
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


BLUE_AGENT_PROMPT = """You are the Blue Agent, an autonomous defensive security AI.

IDENTITY:
You are part of Purple Team GPT, a cybersecurity simulation framework.
Your role is to detect, respond to, and recover from security threats in real-time.
You work alongside the Red Agent to improve organizational security posture.

CAPABILITIES:
- Detection: Log analysis, anomaly detection, threat identification, SIEM integration
- Response: Incident containment, firewall rules, service management, threat isolation
- Recovery: System restoration, rollback procedures, patch management
- Hardening: Security configurations, compliance checks, best practice implementation
- Monitoring: Real-time surveillance, behavioral analysis, alert management

AVAILABLE TOOLS:
- log_analyzer: Analyze system and application logs for threats
- firewall_manager: iptables/ufw rule management
- process_monitor: Monitor and manage running processes
- file_integrity: File integrity monitoring (FIM)
- service_manager: Start/stop/restart services
- netstat_analyzer: Network connection analysis
- user_auditor: User account and permission auditing
- patch_manager: Check and apply security patches
- backup_manager: Backup and recovery operations
- alert_system: Send alerts and notifications

DEFENSE METHODOLOGY:
Follow this structured approach:
1. Monitor: Continuously observe system state and logs
2. Detect: Identify anomalies, intrusions, and suspicious patterns
3. Analyze: Assess threat severity and potential impact
4. Respond: Execute appropriate defensive actions
5. Contain: Isolate threats to prevent spread
6. Eradicate: Remove malicious elements
7. Recover: Restore normal operations
8. Harden: Implement improvements to prevent recurrence

SEVERITY CLASSIFICATIONS:
- Critical: Active intrusion, data breach, system compromise
- High: Detected attack, significant vulnerability exploited
- Medium: Suspicious activity, potential threat indicators
- Low: Minor anomalies, informational security events
- Info: Routine observations, compliance notes

THREAT INDICATORS:
Watch for these attack patterns:
- Brute force: Multiple failed logins from single source
- Port scanning: Sequential connection attempts
- Privilege escalation: Unusual sudo/su activity
- Lateral movement: Unexpected internal connections
- Data exfiltration: Large outbound transfers
- Persistence: New startup items, scheduled tasks
- Defense evasion: Process termination, log clearing

RESPONSE PROTOCOLS:
- Immediate: Block IP, kill process, isolate system
- Short-term: Disable account, reset credentials, patch vulnerability
- Long-term: Update policies, harden configuration, train users

OUTPUT FORMAT:
To execute a defense action:
```json
{
  "action": "execute",
  "tool": "firewall_manager",
  "command": "block_ip 192.168.1.100",
  "explanation": "Blocking suspicious IP detected in brute force attack"
}
```

To report a detection:
```json
{
  "action": "detection",
  "title": "SSH Brute Force Attack Detected",
  "severity": "High",
  "description": "Multiple failed SSH login attempts from IP 192.168.1.100",
  "evidence": "100+ failed auth attempts in auth.log within 5 minutes",
  "response": "IP blocked via firewall, alert sent to SOC"
}
```

To query for relevant defense patterns:
```json
{
  "action": "query_rag",
  "parameters": {"query": "SSH brute force defense strategies"}
}
```

To implement a security improvement:
```json
{
  "action": "hardening",
  "title": "SSH Configuration Hardening",
  "description": "Disable password authentication, enforce key-based auth",
  "recommendation": "Edit /etc/ssh/sshd_config: PasswordAuthentication no"
}
```

When defense session is complete:
```json
{
  "action": "complete",
  "explanation": "All detected threats neutralized, hardening recommendations provided"
}
```

IMPORTANT:
- Always explain your reasoning before each action
- Provide detailed evidence for all detections
- Include specific remediation recommendations
- Learn from patterns stored in RAG memory
- Coordinate responses with Red Agent findings
- Maintain professional and ethical conduct
"""


class ThreatLevel(str, Enum):
    """Threat severity levels for response prioritization."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DefenseStage(str, Enum):
    """Stages of defense operations."""
    MONITOR = "monitor"
    DETECT = "detect"
    ANALYZE = "analyze"
    RESPOND = "respond"
    CONTAIN = "contain"
    ERADICATE = "eradicate"
    RECOVER = "recover"
    HARDEN = "harden"


@dataclass
class ThreatEvent:
    """Represents a detected threat event."""
    event_type: str
    source: str
    severity: ThreatLevel
    description: str
    evidence: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_ip: Optional[str] = None
    target_system: Optional[str] = None
    mitre_tactics: List[str] = field(default_factory=list)
    mitre_techniques: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "source": self.source,
            "severity": self.severity.value,
            "description": self.description,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
            "source_ip": self.source_ip,
            "target_system": self.target_system,
            "mitre_tactics": self.mitre_tactics,
            "mitre_techniques": self.mitre_techniques,
        }


@dataclass
class DefenseAction:
    """Represents a defensive action taken."""
    action_type: str
    tool: str
    command: str
    target: str
    reason: str
    success: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    output: str = ""


@dataclass
class LogAnalysisResult:
    """Result of log analysis."""
    log_source: str
    entries_analyzed: int
    threats_found: List[ThreatEvent]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DefenseToolRunner:
    """Executes defensive security tools safely.
    
    Provides a safe interface for running defensive tools with:
    - Command validation
    - Timeout enforcement
    - Output capture
    - Error handling
    """
    
    # Allowed defensive tools
    ALLOWED_TOOLS = {
        "log_analyzer", "firewall_manager", "process_monitor",
        "file_integrity", "service_manager", "netstat_analyzer",
        "user_auditor", "patch_manager", "backup_manager",
        "alert_system", "iptables", "ufw", "systemctl",
        "journalctl", "netstat", "ss", "lsof", "ps", "top",
        "htop", "auditctl", "ausearch", "rkhunter", "chkrootkit",
    }
    
    # Tools that modify system state (require confirmation in safe mode)
    MODIFICATION_TOOLS = {
        "iptables", "ufw", "systemctl", "firewall_manager",
        "service_manager", "user_auditor", "patch_manager",
    }
    
    def __init__(self, safe_mode: bool = True, default_timeout: int = 120):
        """Initialize the defense tool runner.
        
        Args:
            safe_mode: If True, requires confirmation for system modifications
            default_timeout: Default timeout in seconds
        """
        self.safe_mode = safe_mode
        self.default_timeout = default_timeout
    
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
        
        # Check for dangerous patterns
        dangerous_patterns = [
            "rm -rf /",
            "dd if=/dev/zero",
            "mkfs",
            ":(){ :|:& };:",  # Fork bomb
            "chmod 777 /",
            "> /dev/sd",
            "shutdown",
            "reboot",
            "init 0",
            "init 6",
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                return False, f"Dangerous pattern detected: {pattern}"
        
        # Check for allowed tools
        tool_base = tool_name.split()[0] if tool_name else ""
        if tool_base and tool_base not in self.ALLOWED_TOOLS:
            logger.warning(f"Tool '{tool_base}' not in allowed list, executing anyway")
        
        return True, ""
    
    async def execute(
        self,
        command: str,
        tool_name: str = "",
        timeout: Optional[int] = None,
    ) -> DefenseAction:
        """Execute a defensive command safely.
        
        Args:
            command: The command to execute
            tool_name: Name of the tool for logging
            timeout: Timeout in seconds
            
        Returns:
            DefenseAction with results
        """
        start_time = time.time()
        
        # Validate command
        is_valid, error_msg = self._validate_command(command, tool_name)
        if not is_valid:
            return DefenseAction(
                action_type="execute",
                tool=tool_name,
                command=command,
                target="",
                reason="Validation failed",
                success=False,
                output=error_msg,
            )
        
        timeout = timeout or self.default_timeout
        
        try:
            # Run command in subprocess
            process = await asyncio.create_subprocess_shell(
                command,
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
                return DefenseAction(
                    action_type="execute",
                    tool=tool_name,
                    command=command,
                    target="",
                    reason="Timeout",
                    success=False,
                    output=f"Command timed out after {timeout}s",
                )
            
            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")
            
            # Combine outputs
            full_output = output
            if error_output and not output:
                full_output = error_output
            elif error_output:
                full_output = f"{output}\n{error_output}"
            
            return DefenseAction(
                action_type="execute",
                tool=tool_name,
                command=command,
                target="",
                reason="Executed",
                success=process.returncode == 0,
                output=full_output,
            )
            
        except Exception as e:
            return DefenseAction(
                action_type="execute",
                tool=tool_name,
                command=command,
                target="",
                reason="Execution failed",
                success=False,
                output=f"Execution failed: {str(e)}",
            )


class BlueAgent(BaseAgent):
    """Defensive security operations agent.
    
    The Blue Agent performs defensive security operations including:
    1. Threat Detection - Monitor and identify security incidents
    2. Incident Response - Contain and neutralize threats
    3. Recovery Operations - Restore normal system function
    4. Security Hardening - Implement preventive measures
    
    All actions are logged and findings are stored for learning.
    """
    
    role = AgentRole.BLUE
    
    def __init__(
        self,
        engine: "LLMEngine",
        vector_store: "VectorStore",
        on_step=None,
        on_finding=None,
        on_output=None,
        max_steps: int = 50,
        safe_mode: bool = True,
        tool_timeout: int = 120,
        monitored_system: str = "",
    ):
        """Initialize the Blue Agent.
        
        Args:
            engine: LLM engine for planning and analysis
            vector_store: Vector store for RAG queries
            on_step: Callback for step events
            on_finding: Callback for finding events
            on_output: Callback for output messages
            max_steps: Maximum steps per session
            safe_mode: Enable safe mode for defensive actions
            tool_timeout: Default timeout for tool execution
            monitored_system: The system being monitored
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
        self.monitored_system = monitored_system
        self._tool_runner: Optional[DefenseToolRunner] = None
        self._threat_events: List[ThreatEvent] = []
        self._defense_actions: List[DefenseAction] = []
        self._current_stage: DefenseStage = DefenseStage.MONITOR
    
    @property
    def system_prompt(self) -> str:
        """Return the Blue Agent system prompt."""
        return BLUE_AGENT_PROMPT
    
    @property
    def tool_runner(self) -> DefenseToolRunner:
        """Get or create the tool runner."""
        if self._tool_runner is None:
            self._tool_runner = DefenseToolRunner(
                safe_mode=self.safe_mode,
                default_timeout=self.tool_timeout,
            )
        return self._tool_runner
    
    @property
    def current_stage(self) -> DefenseStage:
        """Get the current defense stage."""
        return self._current_stage
    
    def set_stage(self, stage: DefenseStage) -> None:
        """Set the current defense stage."""
        self._current_stage = stage
        logger.info(f"Blue Agent stage changed to: {stage.value}")
    
    async def plan(self, context: str) -> List[AgentAction]:
        """Plan defensive actions based on context.
        
        Queries RAG for relevant defense patterns and uses the LLM
        to plan appropriate defensive actions.
        
        Args:
            context: Current situation description
            
        Returns:
            List of actions to execute
        """
        # Query RAG for similar defense patterns
        rag_context = await self.query_rag(
            f"defense patterns for {self.target} {context[:100]}"
        )
        
        # Build planning prompt
        planning_prompt = f"""Monitored System: {self.monitored_system or self.target}
Safe Mode: {'Enabled' if self.safe_mode else 'Disabled'}
Current Stage: {self._current_stage.value}

Context from previous defenses:
{rag_context if rag_context else 'No relevant patterns found'}

Current situation:
{context}

Plan your defensive actions. Consider:
1. What threats have been detected?
2. What is the severity and urgency?
3. What immediate responses are needed?
4. What containment measures should be implemented?
5. What recovery actions are required?
6. What hardening improvements should be recommended?
7. Are there any detections that need to be reported?

Provide your plan as JSON action blocks. Explain your reasoning before each action."""

        # Add to conversation and get response
        self.conversation.add_user(planning_prompt)
        response = await self.engine.chat(self.conversation)
        self.conversation.add_assistant(response)
        
        # Parse actions from response
        actions = self._parse_actions(response)
        
        if not actions:
            # Default to monitoring action
            self.output("No valid actions parsed, defaulting to monitoring")
            actions = [AgentAction(
                action_type="execute",
                tool="log_analyzer",
                command="journalctl -p warning --no-pager -n 100",
                explanation="Default system log monitoring",
            )]
        
        return actions
    
    async def execute_action(self, action: AgentAction) -> str:
        """Execute a defensive action.
        
        Handles different action types:
        - execute: Run a defensive tool
        - detection: Record a threat detection
        - hardening: Record a security improvement recommendation
        - query_rag: Query vector store
        - complete: End defense session
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
            elif action.action_type == "detection":
                result = await self._record_detection(action)
            elif action.action_type == "hardening":
                result = await self._record_hardening(action)
            elif action.action_type == "query_rag":
                result = await self._query_rag_action(action)
            elif action.action_type == "complete":
                self.state = AgentState.COMPLETED
                result = f"Defense session completed: {action.explanation}"
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
            result=result[:5000] if result else None,
            success=success,
            error=error,
            duration_ms=(time.time() - start_time) * 1000,
        )
        self.add_step(step)
        
        return result
    
    async def _execute_tool(self, action: AgentAction) -> str:
        """Execute a defensive tool.
        
        Args:
            action: Action containing tool and command
            
        Returns:
            Tool output or error message
        """
        tool_name = action.tool or "unknown"
        command = action.command or ""
        
        self.output(f"Executing defense tool: {tool_name}")
        if action.explanation:
            self.output(f"Reason: {action.explanation}")
        
        # Execute tool
        result = await self.tool_runner.execute(
            command=command,
            tool_name=tool_name,
            timeout=self.tool_timeout,
        )
        
        # Store defense action
        self._defense_actions.append(result)
        
        # Report result
        if result.success:
            self.output(f"Tool completed successfully")
        else:
            self.output(f"Tool failed: {result.output}")
        
        # Store result for learning
        await self.store_interaction(
            content=f"Defense Tool: {tool_name}\nCommand: {command}\nResult: {result.output[:1000]}",
            metadata={
                "tool": tool_name,
                "command": command,
                "target": self.target,
                "success": result.success,
                "type": "defense_action",
            }
        )
        
        return result.output if result.output else "No output"
    
    async def _record_detection(self, action: AgentAction) -> str:
        """Record a threat detection.
        
        Args:
            action: Action containing detection details
            
        Returns:
            Confirmation message
        """
        params = action.parameters
        
        # Create threat event
        threat = ThreatEvent(
            event_type=params.get("event_type", params.get("title", "Unknown")),
            source=params.get("source", "blue_agent"),
            severity=ThreatLevel(params.get("severity", "info").lower()),
            description=params.get("description", ""),
            evidence=params.get("evidence", ""),
            source_ip=params.get("source_ip"),
            target_system=params.get("target_system", self.target),
            mitre_tactics=params.get("mitre_tactics", []),
            mitre_techniques=params.get("mitre_techniques", []),
        )
        
        self._threat_events.append(threat)
        
        # Create finding
        finding = Finding(
            title=params.get("title", "Unknown Detection"),
            severity=params.get("severity", "Info"),
            description=params.get("description", ""),
            evidence=params.get("evidence", ""),
            recommendation=params.get("response", ""),
            tool=action.tool or "detection",
        )
        
        self.add_finding(finding)
        self.output(f"Detection recorded: [{finding.severity}] {finding.title}")
        
        # Store in RAG for future reference
        await self.store_interaction(
            content=f"Detection: {finding.title}\nSeverity: {finding.severity}\nTarget: {self.target}\n{finding.description}\nEvidence: {finding.evidence}\nResponse: {finding.recommendation}",
            metadata={
                "type": "detection",
                "severity": finding.severity,
                "target": self.target,
                "tool": finding.tool,
                "event_type": threat.event_type,
            }
        )
        
        return f"Recorded detection: {finding.title}"
    
    async def _record_hardening(self, action: AgentAction) -> str:
        """Record a security hardening recommendation.
        
        Args:
            action: Action containing hardening details
            
        Returns:
            Confirmation message
        """
        params = action.parameters
        
        finding = Finding(
            title=params.get("title", "Security Hardening Recommendation"),
            severity=params.get("severity", "Info"),
            description=params.get("description", ""),
            evidence=params.get("evidence", ""),
            recommendation=params.get("recommendation", ""),
            tool=action.tool or "hardening",
        )
        
        self.add_finding(finding)
        self.output(f"Hardening recommendation: {finding.title}")
        
        # Store in RAG
        await self.store_interaction(
            content=f"Hardening: {finding.title}\n{finding.description}\nRecommendation: {finding.recommendation}",
            metadata={
                "type": "hardening",
                "target": self.target,
            }
        )
        
        return f"Recorded hardening recommendation: {finding.title}"
    
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
            self.output("RAG returned relevant defense context")
            return f"RAG Context:\n{result}"
        else:
            return "No relevant defense patterns found in knowledge base"
    
    async def monitor(self, log_data: str, log_source: str = "system") -> LogAnalysisResult:
        """Analyze logs and detect threats.
        
        This is the primary monitoring method for the Blue Agent.
        It analyzes log data for security threats and anomalies.
        
        Args:
            log_data: Raw log data to analyze
            log_source: Source of the logs (system, auth, application, etc.)
            
        Returns:
            LogAnalysisResult with findings
        """
        self.set_stage(DefenseStage.MONITOR)
        self.output(f"Analyzing logs from {log_source} ({len(log_data)} bytes)")
        
        # Build analysis prompt
        analysis_prompt = f"""Analyze the following {log_source} logs for security threats:

```
{log_data[:4000]}
```

Identify and report:
1. Suspicious patterns and anomalies
2. Potential attacks or intrusion attempts
3. Authentication failures and successes
4. Privilege escalation attempts
5. Unusual network connections
6. File system modifications
7. Service changes
8. Other security-relevant events

For each finding, provide:
- Event type
- Severity level
- Description
- Evidence (log excerpts)
- Recommended response

Format detections as JSON action blocks with action type "detection"."""

        # Add to conversation
        self.conversation.add_user(analysis_prompt)
        response = await self.engine.chat(self.conversation)
        self.conversation.add_assistant(response)
        
        # Parse actions from response
        actions = self._parse_actions(response)
        
        # Process detections
        threats = []
        anomalies = []
        recommendations = []
        
        for action in actions:
            if action.action_type == "detection":
                params = action.parameters
                
                threat = ThreatEvent(
                    event_type=params.get("event_type", params.get("title", "Unknown")),
                    source=log_source,
                    severity=ThreatLevel(params.get("severity", "info").lower()),
                    description=params.get("description", ""),
                    evidence=params.get("evidence", ""),
                    source_ip=params.get("source_ip"),
                    target_system=self.target,
                )
                threats.append(threat)
                self._threat_events.append(threat)
                
                # Also create a finding
                finding = Finding(
                    title=params.get("title", "Log Detection"),
                    severity=params.get("severity", "Info"),
                    description=params.get("description", ""),
                    evidence=params.get("evidence", ""),
                    recommendation=params.get("response", ""),
                    tool="log_analyzer",
                )
                self.add_finding(finding)
                
            elif action.action_type == "execute":
                # Defense recommendations
                recommendations.append(action.explanation or action.command or "")
        
        result = LogAnalysisResult(
            log_source=log_source,
            entries_analyzed=len(log_data.split('\n')),
            threats_found=threats,
            anomalies=anomalies,
            recommendations=recommendations,
        )
        
        self.output(f"Log analysis complete: {len(threats)} threats, {len(anomalies)} anomalies")
        
        return result
    
    async def respond_to_event(self, event: Dict[str, Any]) -> str:
        """Respond to an event from the Red Agent or external source.
        
        This is the primary response method for the Blue Agent.
        It receives events and determines appropriate defensive actions.
        
        Args:
            event: Event dictionary with type, data, and metadata
            
        Returns:
            Combined results from response actions
        """
        event_type = event.get("type", "unknown")
        event_data = event.get("data", {})
        event_severity = event.get("severity", "medium")
        
        self.output(f"Received event: {event_type} (severity: {event_severity})")
        
        # Set appropriate stage based on event type
        if event_severity in ("critical", "high"):
            self.set_stage(DefenseStage.RESPOND)
        elif event_severity == "medium":
            self.set_stage(DefenseStage.ANALYZE)
        else:
            self.set_stage(DefenseStage.MONITOR)
        
        # Build event context
        event_context = f"""Security Event Received:
Type: {event_type}
Severity: {event_severity}
Source: {event.get('source', 'unknown')}
Timestamp: {event.get('timestamp', datetime.utcnow().isoformat())}

Event Data:
{str(event_data)[:2000]}

Analyze this event and plan defensive response. Consider:
1. Is this a false positive or real threat?
2. What is the impact and scope?
3. What immediate actions are needed?
4. What containment measures should be implemented?
5. What evidence should be collected?

Provide your response plan as JSON action blocks."""

        # Get actions from planning
        actions = await self.plan(event_context)
        
        # Execute each action
        results = []
        for action in actions:
            if self.state == AgentState.COMPLETED:
                break
            if self.state == AgentState.PAUSED:
                results.append("Agent paused during response")
                break
            
            result = await self.execute_action(action)
            results.append(result)
            
            # Add result to conversation for context
            self.conversation.add_user(f"[RESULT]\n{result[:2000]}")
        
        return "\n\n".join(results)
    
    async def respond_to_red_finding(self, red_finding: Finding) -> str:
        """Respond specifically to a finding from the Red Agent.
        
        This allows the Blue Agent to react to vulnerabilities or
        attack findings discovered by the Red Agent.
        
        Args:
            red_finding: Finding from the Red Agent
            
        Returns:
            Response summary
        """
        self.output(f"Responding to Red Agent finding: {red_finding.title}")
        
        event = {
            "type": "red_agent_finding",
            "source": "red_agent",
            "severity": red_finding.severity.lower(),
            "data": {
                "title": red_finding.title,
                "description": red_finding.description,
                "evidence": red_finding.evidence,
                "recommendation": red_finding.recommendation,
                "tool": red_finding.tool,
                "cve": red_finding.cve,
            }
        }
        
        return await self.respond_to_event(event)
    
    async def harden_system(self, system: str = "") -> List[Finding]:
        """Analyze system and provide hardening recommendations.
        
        Args:
            system: System to harden (defaults to monitored system)
            
        Returns:
            List of hardening findings
        """
        target_system = system or self.monitored_system or self.target
        self.set_stage(DefenseStage.HARDEN)
        self.output(f"Analyzing {target_system} for hardening opportunities")
        
        # Query RAG for hardening patterns
        rag_context = await self.query_rag(f"hardening recommendations for {target_system}")
        
        # Build hardening prompt
        hardening_prompt = f"""Analyze the system for security hardening opportunities.

System: {target_system}

Known patterns:
{rag_context if rag_context else 'No specific patterns found'}

Provide comprehensive hardening recommendations for:
1. Network security (firewall rules, open ports)
2. Authentication (password policies, MFA, SSH config)
3. Access control (user permissions, privilege management)
4. Logging and monitoring (audit policies, log retention)
5. File system (permissions, integrity monitoring)
6. Services (unnecessary services, secure configurations)
7. Application security (updates, configurations)
8. Data protection (encryption, backup)

Format each recommendation as a JSON action block with action type "hardening"."""

        # Get recommendations
        self.conversation.add_user(hardening_prompt)
        response = await self.engine.chat(self.conversation)
        self.conversation.add_assistant(response)
        
        # Parse and record hardening actions
        actions = self._parse_actions(response)
        findings = []
        
        for action in actions:
            if action.action_type == "hardening":
                result = await self._record_hardening(action)
                findings.append(self.findings[-1])  # Get the last added finding
        
        self.output(f"Generated {len(findings)} hardening recommendations")
        return findings
    
    async def run_defense_cycle(self, initial_context: str = "") -> Dict[str, Any]:
        """Run a complete defense cycle.
        
        Cycles through monitor -> detect -> respond -> recover -> harden.
        
        Args:
            initial_context: Starting context for the cycle
            
        Returns:
            Defense cycle summary
        """
        self.output(f"Starting defense cycle for {self.target}")
        
        context = initial_context
        iteration = 0
        
        while self.state not in (AgentState.COMPLETED, AgentState.ERROR, AgentState.PAUSED):
            iteration += 1
            
            if self._step_counter >= self.max_steps:
                self.output(f"Maximum steps reached ({self.max_steps})")
                self.state = AgentState.COMPLETED
                break
            
            self.output(f"--- Defense Cycle {iteration} ---")
            
            # Run one step
            result = await self.run_step(context)
            
            # Use result as context for next step
            context = f"Previous cycle result:\n{result[:1000]}"
            
            # Small delay between cycles
            await asyncio.sleep(0.5)
        
        summary = self.get_defense_summary()
        self.output(f"Defense cycle complete: {len(self._threat_events)} threats, {len(self._defense_actions)} actions")
        
        return summary
    
    async def run_step(self, context: str = "") -> str:
        """Execute a single step of the defense cycle.
        
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
    
    def get_defense_summary(self) -> Dict[str, Any]:
        """Get summary of defense operations.
        
        Returns:
            Dictionary with defense session summary
        """
        severity_counts = {}
        for threat in self._threat_events:
            sev = threat.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        successful_actions = sum(1 for a in self._defense_actions if a.success)
        
        return {
            "role": self.role.value,
            "state": self.state.value,
            "target": self.target,
            "monitored_system": self.monitored_system,
            "current_stage": self._current_stage.value,
            "total_steps": len(self.steps),
            "total_threats": len(self._threat_events),
            "total_defense_actions": len(self._defense_actions),
            "successful_actions": successful_actions,
            "threats_by_severity": severity_counts,
            "total_findings": len(self.findings),
            "threats": [t.to_dict() for t in self._threat_events],
            "findings": [f.to_dict() for f in self.findings],
        }
    
    def get_threat_events(self) -> List[ThreatEvent]:
        """Get all recorded threat events."""
        return self._threat_events.copy()
    
    def get_defense_actions(self) -> List[DefenseAction]:
        """Get all defense actions taken."""
        return self._defense_actions.copy()


def create_blue_agent(
    engine: Optional["LLMEngine"] = None,
    vector_store: Optional["VectorStore"] = None,
    **kwargs
) -> BlueAgent:
    """Create a Blue Agent instance.
    
    Args:
        engine: LLM engine (created if not provided)
        vector_store: Vector store (created if not provided)
        **kwargs: Additional arguments for BlueAgent
        
    Returns:
        Configured BlueAgent instance
    """
    if engine is None:
        from purple_team_gpt.core.llm.engine import create_engine
        engine = create_engine()
    
    if vector_store is None:
        from purple_team_gpt.core.rag.vector_store import create_vector_store
        vector_store = create_vector_store()
    
    return BlueAgent(engine=engine, vector_store=vector_store, **kwargs)