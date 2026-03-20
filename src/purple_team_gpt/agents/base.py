"""Base agent class for Purple Team GPT.

This module provides the abstract base class for all agents (Red, Blue, Purple),
including common data structures for actions, steps, and findings.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from purple_team_gpt.core.llm.engine import Conversation, LLMEngine
from purple_team_gpt.core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent role types."""
    RED = "red"
    BLUE = "blue"
    PURPLE = "purple"


class AgentState(str, Enum):
    """Agent execution states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentAction:
    """Represents an action the agent wants to take.
    
    Actions can be:
    - execute: Run a tool or command
    - finding: Report a security finding
    - query_rag: Query the vector store for context
    - wait: Pause for a duration
    - complete: Mark assessment as complete
    """
    action_type: str  # "execute", "finding", "query_rag", "wait", "complete"
    tool: Optional[str] = None
    command: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentStep:
    """A single step in agent execution.
    
    Records the action taken and its result for auditing and learning.
    """
    step_num: int
    action: AgentAction
    result: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None


@dataclass
class Finding:
    """A security finding from an agent.
    
    Represents discovered vulnerabilities, misconfigurations, or detections.
    """
    title: str
    severity: str  # Critical, High, Medium, Low, Info
    description: str
    evidence: str = ""
    recommendation: str = ""
    tool: str = ""
    cve: Optional[str] = None
    cvss_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "tool": self.tool,
            "cve": self.cve,
            "cvss_score": self.cvss_score,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseAgent(ABC):
    """Abstract base class for all security agents.
    
    Provides common functionality for:
    - LLM interaction via conversation management
    - RAG context retrieval
    - Action parsing from LLM responses
    - Finding and step tracking
    - Callback notifications
    
    Subclasses must implement:
    - system_prompt property: Agent-specific system prompt
    - plan(): Generate actions based on context
    - execute_action(): Execute a single action
    """
    
    role: AgentRole = AgentRole.PURPLE
    
    def __init__(
        self,
        engine: LLMEngine,
        vector_store: VectorStore,
        on_step: Optional[Callable[[AgentStep], None]] = None,
        on_finding: Optional[Callable[[Finding], None]] = None,
        on_output: Optional[Callable[[str], None]] = None,
        max_steps: int = 50,
    ):
        """Initialize the base agent.
        
        Args:
            engine: LLM engine for conversation
            vector_store: Vector store for RAG queries
            on_step: Callback for step completion
            on_finding: Callback for new findings
            on_output: Callback for output messages
            max_steps: Maximum steps per session
        """
        self.engine = engine
        self.vector_store = vector_store
        self.on_step = on_step
        self.on_finding = on_finding
        self.on_output = on_output
        self.max_steps = max_steps
        
        # Session state
        self.conversation = Conversation()
        self.state = AgentState.IDLE
        self.steps: List[AgentStep] = []
        self.findings: List[Finding] = []
        self.target = ""
        self.scope = ""
        self._step_counter = 0
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent.
        
        The system prompt defines the agent's role, capabilities, rules,
        and output format expectations.
        """
        pass
    
    @abstractmethod
    async def plan(self, context: str) -> List[AgentAction]:
        """Plan next actions based on context.
        
        Args:
            context: Current situation description
            
        Returns:
            List of actions to execute
        """
        pass
    
    @abstractmethod
    async def execute_action(self, action: AgentAction) -> str:
        """Execute a single action.
        
        Args:
            action: The action to execute
            
        Returns:
            Result string from the action
        """
        pass
    
    def initialize(self, target: str, scope: str = "") -> None:
        """Initialize agent for a new session.
        
        Args:
            target: Target system/network for assessment
            scope: Scope restrictions and constraints
        """
        self.target = target
        self.scope = scope
        
        # Reset conversation with system prompt
        self.conversation = Conversation()
        self.conversation.system_prompt = self.system_prompt
        
        # Reset state
        self.steps = []
        self.findings = []
        self._step_counter = 0
        self.state = AgentState.IDLE
        
        logger.info(f"{self.role.value.title()} Agent initialized for target: {target}")
    
    async def query_rag(self, query: str) -> str:
        """Query vector store for relevant context.
        
        Args:
            query: Search query for relevant patterns
            
        Returns:
            Aggregated context string from vector store
        """
        try:
            context = await self.vector_store.get_context(query)
            if context:
                logger.debug(f"RAG returned context ({len(context)} chars)")
            return context
        except Exception as e:
            logger.warning(f"RAG query failed: {e}")
            return ""
    
    def _parse_actions(self, response: str) -> List[AgentAction]:
        """Parse JSON action blocks from LLM response.
        
        Supports multiple JSON blocks wrapped in ```json...``` markers.
        Also attempts to parse raw JSON if no markers found.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            List of parsed AgentAction objects
        """
        actions = []
        
        # Pattern 1: JSON blocks with markers
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        # Pattern 2: Try to find standalone JSON objects
        if not matches:
            # Look for JSON objects starting with {
            json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_obj_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match.strip())
                
                # Handle both 'action' and 'action_type' keys
                action_type = data.get("action") or data.get("action_type", "unknown")
                
                action = AgentAction(
                    action_type=action_type,
                    tool=data.get("tool"),
                    command=data.get("command"),
                    parameters=data.get("parameters", {}),
                    explanation=data.get("explanation", ""),
                )
                
                # For findings, extract finding-specific fields into parameters
                if action_type in ("finding", "detection"):
                    action.parameters = {
                        "title": data.get("title", "Unknown"),
                        "severity": data.get("severity", "Info"),
                        "description": data.get("description", ""),
                        "evidence": data.get("evidence", ""),
                        "recommendation": data.get("recommendation") or data.get("response", ""),
                    }
                
                actions.append(action)
                logger.debug(f"Parsed action: {action_type}")
                
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON action: {match[:100]}... Error: {e}")
            except Exception as e:
                logger.warning(f"Error processing action: {e}")
        
        return actions
    
    def add_finding(self, finding: Finding) -> None:
        """Add a finding and notify callback.
        
        Args:
            finding: The finding to add
        """
        self.findings.append(finding)
        if self.on_finding:
            try:
                self.on_finding(finding)
            except Exception as e:
                logger.warning(f"Finding callback error: {e}")
    
    def add_step(self, step: AgentStep) -> None:
        """Add a step and notify callback.
        
        Args:
            step: The step to add
        """
        self.steps.append(step)
        if self.on_step:
            try:
                self.on_step(step)
            except Exception as e:
                logger.warning(f"Step callback error: {e}")
    
    def output(self, message: str) -> None:
        """Send output to callback.
        
        Args:
            message: Output message to send
        """
        if self.on_output:
            try:
                self.on_output(message)
            except Exception as e:
                logger.warning(f"Output callback error: {e}")
    
    async def store_interaction(self, content: str, metadata: Dict[str, Any]) -> None:
        """Store interaction in vector store for learning.
        
        Args:
            content: The interaction content to store
            metadata: Metadata associated with the interaction
        """
        try:
            collection = f"{self.role.value}_patterns"
            
            # Add role metadata
            metadata["role"] = self.role.value
            metadata["target"] = self.target
            
            await self.vector_store.add(
                collection_name=collection,
                documents=[content],
                metadatas=[metadata],
            )
            logger.debug(f"Stored interaction in {collection}")
            
        except Exception as e:
            logger.warning(f"Failed to store interaction: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of current session.
        
        Returns:
            Dictionary with session summary
        """
        severity_counts = {}
        for finding in self.findings:
            sev = finding.severity
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        return {
            "role": self.role.value,
            "state": self.state.value,
            "target": self.target,
            "scope": self.scope,
            "total_steps": len(self.steps),
            "total_findings": len(self.findings),
            "findings_by_severity": severity_counts,
            "findings": [f.to_dict() for f in self.findings],
        }
    
    def pause(self) -> None:
        """Pause agent execution."""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.PAUSED
            logger.info(f"{self.role.value.title()} Agent paused")
    
    def resume(self) -> None:
        """Resume agent execution."""
        if self.state == AgentState.PAUSED:
            self.state = AgentState.RUNNING
            logger.info(f"{self.role.value.title()} Agent resumed")
    
    def stop(self) -> None:
        """Stop agent execution."""
        self.state = AgentState.ERROR
        logger.info(f"{self.role.value.title()} Agent stopped")