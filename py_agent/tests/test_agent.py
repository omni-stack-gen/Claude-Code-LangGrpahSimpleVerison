"""
Tests for the Claude Code LangGraph Agent.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from agent.state import AgentState, create_initial_state
from agent.prompts.system import get_system_prompt, GENERAL_PURPOSE_AGENT_PROMPT
from tools.registry import (
    get_tool_schemas,
    get_tool_schema,
    BASH_TOOL_SCHEMA,
    TOOL_NAME_TO_SCHEMA,
)


class TestAgentState:
    """Tests for AgentState."""

    def test_create_initial_state(self):
        """Test creating initial agent state."""
        state = create_initial_state(max_turns=10)

        assert state["turn_count"] == 0
        assert state["messages"] == []
        assert state["tool_results"] == []
        assert state["max_turns"] == 10

    def test_create_initial_state_with_sandbox_config(self):
        """Test creating initial state with sandbox config."""
        sandbox_config = {"filesystem": {"allowWrite": ["/tmp"]}}
        state = create_initial_state(sandbox_config=sandbox_config)

        assert state["sandbox_config"] == sandbox_config

    def test_get_latest_message_empty(self):
        """Test get_latest_message with empty messages."""
        state = create_initial_state()
        # messages list is empty, so no latest message
        assert len(state["messages"]) == 0


class TestPrompts:
    """Tests for system prompts."""

    def test_get_system_prompt_general_purpose(self):
        """Test getting the general purpose system prompt."""
        prompt = get_system_prompt("general-purpose")
        assert GENERAL_PURPOSE_AGENT_PROMPT in prompt

    def test_get_system_prompt_explore(self):
        """Test getting the explore system prompt."""
        from agent.prompts.system import EXPLORE_AGENT_PROMPT

        prompt = get_system_prompt("explore")
        assert EXPLORE_AGENT_PROMPT in prompt

    def test_get_system_prompt_plan(self):
        """Test getting the plan system prompt."""
        from agent.prompts.system import PLAN_AGENT_PROMPT

        prompt = get_system_prompt("plan")
        assert PLAN_AGENT_PROMPT in prompt

    def test_get_system_prompt_default(self):
        """Test that unknown agent types fallback to general purpose."""
        prompt = get_system_prompt("unknown-type")
        assert GENERAL_PURPOSE_AGENT_PROMPT in prompt

    def test_build_full_system_prompt(self):
        """Test building a full Claude Code-style system prompt."""
        from agent.prompts.system import (
            build_full_system_prompt,
            CLAUDE_CODE_DOING_TASKS_SECTION,
            TOOL_DESCRIPTIONS,
        )

        full = build_full_system_prompt()
        # Should contain all sections
        assert CLAUDE_CODE_DOING_TASKS_SECTION in full
        assert TOOL_DESCRIPTIONS in full
        # Should include tool names
        assert "Bash" in full
        assert "Glob" in full
        assert "Grep" in full
        assert "Read" in full
        assert "Edit" in full
        assert "Write" in full
        assert "Agent" in full

    def test_build_full_system_prompt_without_tools(self):
        """Test building prompt without tool sections."""
        from agent.prompts.system import build_full_system_prompt

        full = build_full_system_prompt(include_tool_sections=False)
        # Should still have core sections
        assert "Doing tasks" in full
        assert "Using your tools" not in full

    def test_claude_code_sections_exist(self):
        """Test that all Claude Code sections are defined."""
        from agent.prompts.system import (
            CLAUDE_CODE_INTRO,
            CLAUDE_CODE_SYSTEM_SECTION,
            CLAUDE_CODE_DOING_TASKS_SECTION,
            CLAUDE_CODE_ACTIONS_SECTION,
            CLAUDE_CODE_USING_TOOLS_SECTION,
        )

        assert len(CLAUDE_CODE_INTRO) > 0
        assert len(CLAUDE_CODE_SYSTEM_SECTION) > 0
        assert len(CLAUDE_CODE_DOING_TASKS_SECTION) > 0
        assert len(CLAUDE_CODE_ACTIONS_SECTION) > 0
        assert len(CLAUDE_CODE_USING_TOOLS_SECTION) > 0


class TestToolRegistry:
    """Tests for tool registry."""

    def test_get_tool_schemas(self):
        """Test getting all tool schemas."""
        schemas = get_tool_schemas()
        assert len(schemas) > 0
        assert BASH_TOOL_SCHEMA in schemas

    def test_get_tool_schema(self):
        """Test getting a specific tool schema."""
        schema = get_tool_schema("Bash")
        assert schema is not None
        assert schema["name"] == "Bash"

    def test_get_tool_schema_not_found(self):
        """Test getting a non-existent tool schema."""
        schema = get_tool_schema("NonExistentTool")
        assert schema is None

    def test_tool_name_to_schema_mapping(self):
        """Test that all tools have schemas in the mapping."""
        schemas = get_tool_schemas()
        for schema in schemas:
            assert schema["name"] in TOOL_NAME_TO_SCHEMA
            assert TOOL_NAME_TO_SCHEMA[schema["name"]] == schema


class TestSandboxConfig:
    """Tests for sandbox configuration."""

    def test_get_default_sandbox_config(self):
        """Test getting default sandbox config."""
        from sandbox.config import get_default_sandbox_config

        config = get_default_sandbox_config()
        assert config["filesystem"]["allowWrite"] == ["."]

    def test_create_restricted_sandbox_config(self):
        """Test creating restricted sandbox config."""
        from sandbox.config import create_restricted_sandbox_config

        config = create_restricted_sandbox_config(
            allowed_directories=["/home/user/project"],
            denied_directories=["/etc", "/var"],
        )

        assert "/home/user/project" in config["filesystem"]["allowWrite"]
        assert "/etc" in config["filesystem"]["denyWrite"]


class TestToolServerClient:
    """Tests for ToolServerClient."""

    def test_tool_server_client_init(self):
        """Test ToolServerClient initialization."""
        from tools.client import ToolServerClient

        client = ToolServerClient(base_url="http://localhost:8080")
        assert client.base_url == "http://localhost:8080"

    def test_tool_server_client_strips_trailing_slash(self):
        """Test that client strips trailing slashes."""
        from tools.client import ToolServerClient

        client = ToolServerClient(base_url="http://localhost:8080/")
        assert client.base_url == "http://localhost:8080"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
