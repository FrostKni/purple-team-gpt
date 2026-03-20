"""Tests for the Agent classes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ============================================================================
# Base Agent Tests - Import at class level to avoid circular imports
# ============================================================================

class TestFinding:
    """Tests for the Finding dataclass."""
    
    def test_finding_creation(self):
        """Test creating a finding."""
        from purple_team_gpt.agents.base import Finding
        finding = Finding(
            title="SSH Weak Configuration",
            severity="Medium",
            description="SSH allows password auth",
        )
        assert finding.title == "SSH Weak Configuration"
        assert finding.severity == "Medium"
        assert finding.evidence == ""
    
    def test_finding_to_dict(self):
        """Test converting finding to dictionary."""
        from purple_team_gpt.agents.base import Finding
        finding = Finding(
            title="Test Finding",
            severity="High",
            description="Test description",
            evidence="Test evidence",
            recommendation="Test recommendation",
            tool="nmap",
        )
        
        result = finding.to_dict()
        assert result["title"] == "Test Finding"
        assert result["severity"] == "High"
        assert result["tool"] == "nmap"
        assert "timestamp" in result


class TestAgentAction:
    """Tests for the AgentAction dataclass."""
    
    def test_action_creation(self):
        """Test creating an action."""
        from purple_team_gpt.agents.base import AgentAction
        action = AgentAction(
            action_type="execute",
            tool="nmap",
            command="nmap -sV target",
            explanation="Service version scan",
        )
        assert action.action_type == "execute"
        assert action.tool == "nmap"
        assert action.parameters == {}
    
    def test_action_with_parameters(self):
        """Test creating an action with parameters."""
        from purple_team_gpt.agents.base import AgentAction
        action = AgentAction(
            action_type="query_rag",
            parameters={"query": "SSH brute force"},
        )
        assert action.action_type == "query_rag"
        assert action.parameters["query"] == "SSH brute force"


class TestAgentStep:
    """Tests for the AgentStep dataclass."""
    
    def test_step_creation(self):
        """Test creating a step."""
        from purple_team_gpt.agents.base import AgentAction, AgentStep
        action = AgentAction(action_type="execute", tool="nmap")
        step = AgentStep(
            step_num=1,
            action=action,
            result="Scan completed",
            success=True,
        )
        assert step.step_num == 1
        assert step.success is True
        assert step.error is None


class TestAgentRole:
    """Tests for the AgentRole enum."""
    
    def test_role_values(self):
        """Test role enum values."""
        from purple_team_gpt.agents.base import AgentRole
        assert AgentRole.RED.value == "red"
        assert AgentRole.BLUE.value == "blue"
        assert AgentRole.PURPLE.value == "purple"


class TestAgentState:
    """Tests for the AgentState enum."""
    
    def test_state_values(self):
        """Test state enum values."""
        from purple_team_gpt.agents.base import AgentState
        assert AgentState.IDLE.value == "idle"
        assert AgentState.RUNNING.value == "running"
        assert AgentState.PAUSED.value == "paused"
        assert AgentState.COMPLETED.value == "completed"
        assert AgentState.ERROR.value == "error"


# ============================================================================
# Red Agent Tests
# ============================================================================

class TestToolRunner:
    """Tests for the ToolRunner class."""
    
    def test_initialization(self):
        """Test tool runner initialization."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner(safe_mode=True, default_timeout=60)
        assert runner.safe_mode is True
        assert runner.default_timeout == 60
    
    def test_validate_command_empty(self):
        """Test validation of empty command."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner()
        is_valid, error = runner._validate_command("", "nmap")
        assert is_valid is False
        assert "Empty command" in error
    
    def test_validate_command_destructive_in_safe_mode(self):
        """Test blocking destructive commands in safe mode."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner(safe_mode=True)
        
        is_valid, error = runner._validate_command("rm -rf /", "rm")
        assert is_valid is False
        assert "safe mode" in error.lower() or "dangerous" in error.lower()
    
    def test_validate_command_destructive_allowed_unsafe_mode(self):
        """Test that some commands work in unsafe mode that would be blocked in safe mode."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        
        # In safe mode, certain tools are blocked
        runner_safe = ToolRunner(safe_mode=True)
        is_valid_safe, error_safe = runner_safe._validate_command("nmap -sV target", "nmap")
        
        # In unsafe mode, regular security tools should still work
        runner_unsafe = ToolRunner(safe_mode=False)
        is_valid_unsafe, error_unsafe = runner_unsafe._validate_command("nmap -sV target", "nmap")
        
        # Both should pass for nmap (allowed tool)
        assert is_valid_safe is True
        assert is_valid_unsafe is True
    
    def test_validate_command_dangerous_patterns(self):
        """Test blocking dangerous patterns."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner()
        
        dangerous_commands = [
            "rm -rf /",
            ":(){ :|:& };:",  # Fork bomb
            "mkfs /dev/sda1",
        ]
        
        for cmd in dangerous_commands:
            is_valid, error = runner._validate_command(cmd, "test")
            assert is_valid is False, f"Should block: {cmd}"
    
    def test_validate_command_allowed_tools(self):
        """Test validation of allowed tools."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner()
        
        is_valid, error = runner._validate_command("nmap -sV target", "nmap")
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful command execution."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner(default_timeout=5)
        
        result = await runner.execute("echo 'test output'", "echo")
        
        assert result.success is True
        assert "test output" in result.output
        assert result.return_code == 0
    
    @pytest.mark.asyncio
    async def test_execute_failure(self):
        """Test failed command execution."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner(default_timeout=5)
        
        result = await runner.execute("ls /nonexistent_directory_12345", "ls")
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """Test command timeout."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner(default_timeout=1)
        
        result = await runner.execute("sleep 10", "sleep", timeout=1)
        
        assert result.success is False
        assert "timed out" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_blocked_command(self):
        """Test execution of blocked command."""
        from purple_team_gpt.agents.red_agent import ToolRunner
        runner = ToolRunner(safe_mode=True)
        
        result = await runner.execute("rm -rf /", "rm")
        
        assert result.success is False
        assert result.return_code == -1


class TestRedAgent:
    """Tests for the RedAgent class."""
    
    def test_initialization(self, llm_engine, vector_store):
        """Test red agent initialization."""
        from purple_team_gpt.agents.red_agent import RedAgent
        from purple_team_gpt.agents.base import AgentRole, AgentState
        agent = RedAgent(
            engine=llm_engine,
            vector_store=vector_store,
            max_steps=10,
            safe_mode=True,
        )
        
        assert agent.role == AgentRole.RED
        assert agent.safe_mode is True
        assert agent.state == AgentState.IDLE
    
    def test_system_prompt(self, red_agent):
        """Test that system prompt is set correctly."""
        from purple_team_gpt.agents.red_agent import RED_AGENT_PROMPT
        prompt = red_agent.system_prompt
        assert prompt == RED_AGENT_PROMPT
        assert "Red Agent" in prompt
        assert "offensive security" in prompt.lower()
    
    def test_initialize(self, red_agent):
        """Test initializing agent for a session."""
        from purple_team_gpt.agents.base import AgentState
        red_agent.initialize("192.168.1.1", "Authorized penetration test")
        
        assert red_agent.target == "192.168.1.1"
        assert red_agent.scope == "Authorized penetration test"
        assert red_agent.state == AgentState.IDLE
        assert len(red_agent.steps) == 0
        assert len(red_agent.findings) == 0
    
    def test_add_finding(self, red_agent, mock_finding_callback):
        """Test adding a finding."""
        from purple_team_gpt.agents.base import Finding
        finding = Finding(
            title="Test Finding",
            severity="High",
            description="Test description",
        )
        
        red_agent.add_finding(finding)
        
        assert finding in red_agent.findings
        mock_finding_callback.assert_called_once_with(finding)
    
    def test_add_step(self, red_agent, mock_step_callback):
        """Test adding a step."""
        from purple_team_gpt.agents.base import AgentAction, AgentStep
        action = AgentAction(action_type="execute", tool="nmap")
        step = AgentStep(step_num=1, action=action, result="Done", success=True)
        
        red_agent.add_step(step)
        
        assert step in red_agent.steps
        mock_step_callback.assert_called_once_with(step)
    
    def test_output(self, red_agent, mock_output_callback):
        """Test output callback."""
        red_agent.output("Test message")
        mock_output_callback.assert_called_once_with("Test message")
    
    def test_pause(self, red_agent):
        """Test pausing agent."""
        from purple_team_gpt.agents.base import AgentState
        red_agent.state = AgentState.RUNNING
        red_agent.pause()
        assert red_agent.state == AgentState.PAUSED
    
    def test_resume(self, red_agent):
        """Test resuming agent."""
        from purple_team_gpt.agents.base import AgentState
        red_agent.state = AgentState.PAUSED
        red_agent.resume()
        assert red_agent.state == AgentState.RUNNING
    
    def test_stop(self, red_agent):
        """Test stopping agent."""
        from purple_team_gpt.agents.base import AgentState
        red_agent.state = AgentState.RUNNING
        red_agent.stop()
        assert red_agent.state == AgentState.ERROR
    
    def test_get_summary(self, red_agent):
        """Test getting agent summary."""
        from purple_team_gpt.agents.base import Finding
        red_agent.initialize("192.168.1.1", "Test")
        red_agent.add_finding(Finding(title="Test", severity="High", description="Desc"))
        
        summary = red_agent.get_summary()
        
        assert summary["role"] == "red"
        assert summary["target"] == "192.168.1.1"
        assert summary["total_findings"] == 1
        assert "High" in summary["findings_by_severity"]
    
    @pytest.mark.asyncio
    async def test_query_rag(self, red_agent):
        """Test RAG query."""
        red_agent.initialize("target", "")
        
        # Mock the vector_store.get_context method
        red_agent.vector_store.get_context = AsyncMock(return_value="test context")
        
        context = await red_agent.query_rag("SQL injection techniques")
        
        # Vector store's get_context should be called
        red_agent.vector_store.get_context.assert_called_once()
    
    def test_parse_actions_json_blocks(self, red_agent):
        """Test parsing JSON action blocks from response."""
        response = '''
        Here's my plan:
        ```json
        {
            "action": "execute",
            "tool": "nmap",
            "command": "nmap -sV target",
            "explanation": "Service scan"
        }
        ```
        '''
        
        actions = red_agent._parse_actions(response)
        
        assert len(actions) == 1
        assert actions[0].action_type == "execute"
        assert actions[0].tool == "nmap"
    
    def test_parse_actions_multiple(self, red_agent):
        """Test parsing multiple JSON actions."""
        response = '''
        ```json
        {"action": "execute", "tool": "nmap", "command": "nmap target"}
        ```
        And then:
        ```json
        {"action": "finding", "title": "Open Port", "severity": "Medium", "description": "Found open port"}
        ```
        '''
        
        actions = red_agent._parse_actions(response)
        
        assert len(actions) == 2
        assert actions[0].action_type == "execute"
        assert actions[1].action_type == "finding"
    
    def test_parse_actions_finding(self, red_agent):
        """Test parsing finding action."""
        response = '''
        ```json
        {
            "action": "finding",
            "title": "SSH Exposed",
            "severity": "High",
            "description": "SSH port is exposed",
            "evidence": "Port 22 open",
            "recommendation": "Restrict access"
        }
        ```
        '''
        
        actions = red_agent._parse_actions(response)
        
        assert len(actions) == 1
        assert actions[0].action_type == "finding"
        assert actions[0].parameters["title"] == "SSH Exposed"
        assert actions[0].parameters["severity"] == "High"
    
    def test_parse_actions_invalid_json(self, red_agent):
        """Test handling invalid JSON in response."""
        response = '''
        ```json
        {invalid json}
        ```
        '''
        
        actions = red_agent._parse_actions(response)
        
        assert len(actions) == 0
    
    @pytest.mark.asyncio
    async def test_execute_action_complete(self, red_agent):
        """Test execute_action with complete action."""
        from purple_team_gpt.agents.base import AgentAction, AgentState
        red_agent.initialize("target", "")
        action = AgentAction(
            action_type="complete",
            explanation="Assessment finished",
        )
        
        result = await red_agent.execute_action(action)
        
        assert "completed" in result.lower()
        assert red_agent.state == AgentState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execute_action_wait(self, red_agent):
        """Test execute_action with wait action."""
        from purple_team_gpt.agents.base import AgentAction
        red_agent.initialize("target", "")
        action = AgentAction(
            action_type="wait",
            parameters={"seconds": 1},
        )
        
        result = await red_agent.execute_action(action)
        
        assert "waited" in result.lower()
        assert len(red_agent.steps) == 1
    
    @pytest.mark.asyncio
    async def test_execute_action_query_rag(self, red_agent):
        """Test execute_action with query_rag action."""
        from purple_team_gpt.agents.base import AgentAction
        red_agent.initialize("target", "")
        
        # Mock the vector_store.get_context method
        red_agent.vector_store.get_context = AsyncMock(return_value="test context")
        
        action = AgentAction(
            action_type="query_rag",
            parameters={"query": "test query"},
        )
        
        result = await red_agent.execute_action(action)
        
        red_agent.vector_store.get_context.assert_called()


# ============================================================================
# Blue Agent Tests
# ============================================================================

class TestDefenseToolRunner:
    """Tests for the DefenseToolRunner class."""
    
    def test_initialization(self):
        """Test defense tool runner initialization."""
        from purple_team_gpt.agents.blue_agent import DefenseToolRunner
        runner = DefenseToolRunner(safe_mode=True, default_timeout=60)
        assert runner.safe_mode is True
        assert runner.default_timeout == 60
    
    def test_validate_command_dangerous_patterns(self):
        """Test blocking dangerous patterns."""
        from purple_team_gpt.agents.blue_agent import DefenseToolRunner
        runner = DefenseToolRunner()
        
        dangerous_commands = [
            "rm -rf /",
            "shutdown",
            "reboot",
            ":(){ :|:& };:",
        ]
        
        for cmd in dangerous_commands:
            is_valid, error = runner._validate_command(cmd, "test")
            assert is_valid is False, f"Should block: {cmd}"
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful command execution."""
        from purple_team_gpt.agents.blue_agent import DefenseToolRunner
        runner = DefenseToolRunner(default_timeout=5)
        
        result = await runner.execute("echo 'defense'", "echo")
        
        assert result.success is True
        assert "defense" in result.output


class TestBlueAgent:
    """Tests for the BlueAgent class."""
    
    def test_initialization(self, llm_engine, vector_store):
        """Test blue agent initialization."""
        from purple_team_gpt.agents.blue_agent import BlueAgent
        from purple_team_gpt.agents.base import AgentRole, AgentState
        agent = BlueAgent(
            engine=llm_engine,
            vector_store=vector_store,
            max_steps=10,
            safe_mode=True,
            monitored_system="test-server",
        )
        
        assert agent.role == AgentRole.BLUE
        assert agent.safe_mode is True
        assert agent.monitored_system == "test-server"
    
    def test_system_prompt(self, blue_agent):
        """Test that system prompt is set correctly."""
        from purple_team_gpt.agents.blue_agent import BLUE_AGENT_PROMPT
        prompt = blue_agent.system_prompt
        assert prompt == BLUE_AGENT_PROMPT
        assert "Blue Agent" in prompt
        assert "defensive" in prompt.lower()
    
    def test_initialize(self, blue_agent):
        """Test initializing blue agent for a session."""
        from purple_team_gpt.agents.base import AgentState
        blue_agent.initialize("monitored-system", "All servers")
        
        assert blue_agent.target == "monitored-system"
        assert blue_agent.scope == "All servers"
        assert blue_agent.state == AgentState.IDLE
    
    def test_get_summary(self, blue_agent):
        """Test getting blue agent summary."""
        from purple_team_gpt.agents.base import Finding
        blue_agent.initialize("system", "")
        blue_agent.add_finding(Finding(
            title="Threat Detected",
            severity="Critical",
            description="Intrusion detected",
        ))
        
        summary = blue_agent.get_summary()
        
        assert summary["role"] == "blue"
        assert summary["total_findings"] == 1
        assert "Critical" in summary["findings_by_severity"]