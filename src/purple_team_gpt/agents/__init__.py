"""Agent implementations for Purple Team GPT.

This module provides the agent system for autonomous security operations:
- BaseAgent: Abstract base class for all agents
- RedAgent: Offensive security testing agent
- BlueAgent: Defensive security operations agent
- AgentRole: Enumeration of agent roles (Red, Blue, Purple)
- AgentState: Enumeration of agent states
- AgentAction: Dataclass for agent actions
- AgentStep: Dataclass for execution steps
- Finding: Dataclass for security findings

Usage:
    from purple_team_gpt.agents import RedAgent, BlueAgent, BaseAgent, Finding
    from purple_team_gpt.core.llm import create_engine
    from purple_team_gpt.core.rag import create_vector_store
    
    # Create offensive agent
    engine = create_engine()
    vector_store = create_vector_store()
    red_agent = RedAgent(engine, vector_store)
    red_agent.initialize(target="192.168.1.1", scope="Authorized penetration test")
    summary = await red_agent.run_assessment()
    
    # Create defensive agent
    blue_agent = BlueAgent(engine, vector_store)
    blue_agent.initialize(target="192.168.1.1")
    result = await blue_agent.monitor(log_data, log_source="auth")
"""

from purple_team_gpt.agents.base import (
    AgentAction,
    AgentRole,
    AgentState,
    AgentStep,
    BaseAgent,
    Finding,
)
from purple_team_gpt.agents.red_agent import (
    RED_AGENT_PROMPT,
    RedAgent,
    ToolResult,
    ToolRunner,
    create_red_agent,
)
from purple_team_gpt.agents.blue_agent import (
    BLUE_AGENT_PROMPT,
    BlueAgent,
    DefenseAction,
    DefenseStage,
    DefenseToolRunner,
    LogAnalysisResult,
    ThreatEvent,
    ThreatLevel,
    create_blue_agent,
)

__all__ = [
    # Base classes and types
    "BaseAgent",
    "AgentRole",
    "AgentState",
    "AgentAction",
    "AgentStep",
    "Finding",
    # Red Agent
    "RedAgent",
    "RED_AGENT_PROMPT",
    "ToolRunner",
    "ToolResult",
    "create_red_agent",
    # Blue Agent
    "BlueAgent",
    "BLUE_AGENT_PROMPT",
    "DefenseToolRunner",
    "DefenseAction",
    "DefenseStage",
    "LogAnalysisResult",
    "ThreatEvent",
    "ThreatLevel",
    "create_blue_agent",
]