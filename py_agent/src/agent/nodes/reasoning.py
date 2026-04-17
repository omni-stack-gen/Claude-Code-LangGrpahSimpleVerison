"""
Reasoning node for LangGraph - handles LLM calls to Claude.

This module implements the core LLM reasoning node that:
1. Takes message history from agent state
2. Injects Claude Code system prompt
3. Calls the LLM with tool bindings
4. Returns response (with optional tool calls)
"""
import os
from typing import Literal, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.messages import SystemMessage
from langchain_anthropic import ChatAnthropic

from ..state import AgentState, has_tool_calls, get_latest_message
from ..prompts import build_full_system_prompt


def create_reasoning_node(
    model_name: str = "claude-opus-4-6",
    api_key: str | None = None,
    agent_type: str = "general-purpose",
):
    """Create a reasoning node that calls the Claude LLM.

    Args:
        model_name: The Claude model to use (e.g., "claude-opus-4-6")
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env if not provided)
        agent_type: Agent type for system prompt ("general-purpose", "explore", "plan")

    Returns:
        An async node function that processes messages through the LLM
    """

    async def reasoning_node(state: AgentState) -> dict:
        """Process the current state and generate a response.

        This node:
        1. Takes the current message history
        2. Injects Claude Code system prompt
        3. Calls the LLM with tool definitions
        4. Returns the model's response (which may include tool calls)
        """
        messages = state["messages"]
        turn_count = state["turn_count"]
        max_turns = state["max_turns"]

        # Check if we've exceeded max turns
        if turn_count >= max_turns:
            return {
                "messages": [
                    AIMessage(
                        content="Maximum turns exceeded. Please review the work done so far."
                    )
                ]
            }

        # Build system prompt with Claude Code guidelines
        system_prompt = build_full_system_prompt(
            agent_type=agent_type,
            include_tool_sections=True,
        )

        # Create system message
        system_msg = SystemMessage(content=system_prompt)

        # Combine system + user messages
        all_messages: Sequence[BaseMessage] = [system_msg]
        all_messages = all_messages + list(messages)

        # Initialize the LLM
        llm_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        llm = ChatAnthropic(
            model=model_name,
            anthropic_api_key=llm_api_key,
            temperature=1.0,  # Claude Code default
        )

        # Get tool definitions for the LLM
        from ..tools.registry import get_tool_schemas

        tool_schemas = get_tool_schemas()

        # Bind tools using the dict schemas directly
        llm_with_tools = llm.bind_tools(tool_schemas)

        # Call the LLM
        response = await llm_with_tools.ainvoke(all_messages)

        # Increment turn count
        new_turn_count = turn_count + 1

        return {
            "messages": [response],
            "turn_count": new_turn_count,
        }

    return reasoning_node


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine whether to continue to tools or end.

    This is a conditional edge function that checks if the last
    message contains tool calls. If so, route to the tools node.
    Otherwise, end the graph execution.

    Args:
        state: The current agent state

    Returns:
        "tools" if there are tool calls, "end" otherwise
    """
    if has_tool_calls(state):
        return "tools"
    return "end"
