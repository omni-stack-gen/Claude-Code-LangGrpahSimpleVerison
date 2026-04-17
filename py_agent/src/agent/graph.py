"""
LangGraph graph definition for Claude Code Agent.

This module defines the core StateGraph for the Claude Code agent,
with reasoning and tools nodes, connected by conditional edges.
"""
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.graph import END as LANGGRAPH_END

from .state import AgentState, create_initial_state, has_tool_calls
from .nodes.reasoning import create_reasoning_node
from .nodes.tools import create_tools_node
from .prompts import build_full_system_prompt


def create_agent_graph(
    model_name: str = "claude-opus-4-6",
    tool_server_url: str = "http://localhost:8080",
    api_key: str | None = None,
    agent_type: str = "general-purpose",
):
    """Create the Claude Code Agent graph.

    Args:
        model_name: The model to use for reasoning
        tool_server_url: URL of the TypeScript tool server
        api_key: Anthropic API key (optional)
        agent_type: Type of agent ("general-purpose", "explore", "plan")

    Returns:
        A compiled LangGraph StateGraph
    """
    # Create the state graph
    builder = StateGraph(AgentState)

    # Create node functions with agent_type passed
    reasoning_node = create_reasoning_node(
        model_name=model_name,
        api_key=api_key,
        agent_type=agent_type,
    )
    tools_node = create_tools_node(tool_server_url=tool_server_url)

    # Add nodes
    builder.add_node("reasoning", reasoning_node)
    builder.add_node("tools", tools_node)

    # Add edges
    builder.add_edge(START, "reasoning")

    # Conditional edge: after reasoning, either call tools or end
    builder.add_conditional_edges(
        "reasoning",
        has_tool_calls,
        {
            True: "tools",      # has tool calls → tools
            False: END,         # no tool calls → end
        },
    )

    # After tools, loop back to reasoning
    builder.add_edge("tools", "reasoning")

    # Compile the graph
    return builder.compile()


class ClaudeCodeAgent:
    """High-level interface for the Claude Code LangGraph Agent."""

    def __init__(
        self,
        model_name: str = "claude-opus-4-6",
        tool_server_url: str = "http://localhost:8080",
        api_key: str | None = None,
        max_turns: int = 50,
        sandbox_config: dict | None = None,
        agent_type: str = "general-purpose",
    ):
        """Initialize the Claude Code Agent.

        Args:
            model_name: The model to use for reasoning
            tool_server_url: URL of the TypeScript tool server
            api_key: Anthropic API key (optional)
            max_turns: Maximum number of turns before stopping
            sandbox_config: Configuration for the sandbox
            agent_type: Type of agent prompt to use
        """
        self.graph = create_agent_graph(
            model_name=model_name,
            tool_server_url=tool_server_url,
            api_key=api_key,
            agent_type=agent_type,
        )
        self.max_turns = max_turns
        self.sandbox_config = sandbox_config or {}
        self.agent_type = agent_type
        self.tool_server_url = tool_server_url
        self.model_name = model_name

    def run(self, input_message: str) -> AgentState:
        """Run the agent synchronously (blocking).

        Note: Prefer run_async() for production use.

        Args:
            input_message: The user's message

        Returns:
            The final agent state
        """
        import asyncio

        return asyncio.run(self.run_async(input_message))

    async def run_async(self, input_message: str) -> AgentState:
        """Run the agent asynchronously.

        Args:
            input_message: The user's message

        Returns:
            The final agent state
        """
        from langchain_core.messages import HumanMessage

        initial_state = create_initial_state(
            sandbox_config=self.sandbox_config,
            max_turns=self.max_turns,
        )

        initial_state["messages"] = [
            HumanMessage(content=input_message),
        ]

        # Run the graph asynchronously
        final_state = await self.graph.ainvoke(initial_state)
        return final_state

    def run_stream(self, input_message: str):
        """Run the agent with streaming output.

        Args:
            input_message: The user's message

        Yields:
            State updates as the agent runs
        """
        from langchain_core.messages import HumanMessage

        initial_state = create_initial_state(
            sandbox_config=self.sandbox_config,
            max_turns=self.max_turns,
        )

        initial_state["messages"] = [
            HumanMessage(content=input_message),
        ]

        # Run the graph with streaming
        return self.graph.astream(initial_state)

    def run_stream_events(self, input_message: str):
        """Run the agent with streaming events (for async iterators).

        Args:
            input_message: The user's message

        Yields:
            Async iterator of events
        """
        from langchain_core.messages import HumanMessage

        initial_state = create_initial_state(
            sandbox_config=self.sandbox_config,
            max_turns=self.max_turns,
        )

        initial_state["messages"] = [
            HumanMessage(content=input_message),
        ]

        return self.graph.astream_events(initial_state)
