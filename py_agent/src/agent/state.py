"""
Agent state definitions for LangGraph Claude Code Agent.
"""
from typing import Annotated, TypedDict, Sequence
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage


class AgentState(TypedDict):
    """State for the Claude Code LangGraph Agent."""

    messages: Annotated[list[BaseMessage], add_messages]
    turn_count: int
    tool_results: list[dict]
    sandbox_config: dict
    max_turns: int


def get_latest_message(state: AgentState) -> BaseMessage | None:
    """Get the most recent message from agent state."""
    messages = state.get("messages", [])
    if messages:
        return messages[-1]
    return None


def has_tool_calls(state: AgentState) -> bool:
    """Check if the latest message has tool calls."""
    latest = get_latest_message(state)
    if isinstance(latest, AIMessage) and latest.tool_calls:
        return len(latest.tool_calls) > 0
    return False


def create_initial_state(
    sandbox_config: dict | None = None,
    max_turns: int = 50,
) -> AgentState:
    """Create initial agent state."""
    return AgentState(
        messages=[],
        turn_count=0,
        tool_results=[],
        sandbox_config=sandbox_config or {},
        max_turns=max_turns,
    )
