"""
Reasoning node for LangGraph - handles LLM calls to Claude.

This module implements the core LLM reasoning node that:
1. Takes message history from agent state
2. Injects Claude Code system prompt
3. Calls the LLM with retry logic for rate limiting
4. Returns response (with optional tool calls)
"""
import os
import asyncio
import logging
from typing import Literal, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.messages import SystemMessage
from langchain_anthropic import ChatAnthropic

from ..state import AgentState, has_tool_calls, get_latest_message
from ..prompts import build_full_system_prompt

logger = logging.getLogger(__name__)

# Retry configuration for LLM calls
LLM_MAX_RETRIES = 5
LLM_INITIAL_DELAY = 2.0  # seconds - LLM APIs need more time
LLM_MAX_DELAY = 120.0  # seconds
LLM_BACKOFF_MULTIPLIER = 2.0


def calculate_llm_delay(attempt: int) -> float:
    """Calculate delay with exponential backoff and jitter for LLM calls."""
    import random
    delay = min(LLM_INITIAL_DELAY * (LLM_BACKOFF_MULTIPLIER ** attempt), LLM_MAX_DELAY)
    # Add jitter (±10%)
    jitter = delay * 0.1 * (2 * random.random() - 1)
    return max(0.1, delay + jitter)  # Minimum 100ms


def is_llm_overloaded_error(error: Exception) -> bool:
    """Check if an error is a rate limiting / overloaded error from LLM API."""
    error_str = str(error).lower()

    # Anthropic/Minimax rate limit indicators
    if "overloaded" in error_str or "overloaded_error" in error_str:
        return True
    if "rate_limit" in error_str or "rate limit" in error_str:
        return True
    if "429" in error_str:
        return True
    if "529" in error_str:
        return True
    if "service_unavailable" in error_str:
        return True
    if "internal_server_error" in error_str and "500" in error_str:
        return True
    if "api_error" in error_str:
        return True
    if "busy" in error_str:
        return True
    if "try_again" in error_str or "retry" in error_str:
        return True

    # Check for specific exception types
    if hasattr(error, "status_code"):
        code = getattr(error, "status_code", None)
        if code in (429, 500, 502, 503, 504, 509, 529):
            return True

    return False


async def call_llm_with_retry(
    llm,
    messages: Sequence[BaseMessage],
    max_retries: int = LLM_MAX_RETRIES,
):
    """Call the LLM with exponential backoff retry for rate limiting.

    Args:
        llm: The LLM instance (ChatAnthropic)
        messages: The messages to send
        max_retries: Maximum number of retry attempts

    Returns:
        The LLM response

    Raises:
        The last exception if all retries are exhausted
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return await llm.ainvoke(messages)
        except Exception as e:
            last_error = e

            if attempt >= max_retries:
                logger.warning(f"LLM call failed after {max_retries} retries")
                raise

            if not is_llm_overloaded_error(e):
                # Non-retryable error - raise immediately
                logger.debug(f"Non-retryable LLM error: {e}")
                raise

            delay = calculate_llm_delay(attempt)
            error_type = type(e).__name__

            # Get more details from error if available
            error_msg = str(e)
            if len(error_msg) > 150:
                error_msg = error_msg[:150] + "..."

            logger.warning(f"[LLM Retry {attempt + 1}/{max_retries + 1}] {error_type}: {error_msg}")
            logger.info(f"Waiting {delay:.1f}s before retry...")

            await asyncio.sleep(delay)

    # Should not reach here
    raise last_error


def create_reasoning_node(
    model_name: str = "claude-opus-4-6",
    api_key: str | None = None,
    base_url: str | None = None,
    agent_type: str = "general-purpose",
    max_retries: int = LLM_MAX_RETRIES,
):
    """Create a reasoning node that calls the Claude LLM with retry logic.

    Args:
        model_name: The Claude model to use (e.g., "claude-opus-4-6", "MiniMax-M2.7")
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env if not provided)
        base_url: Custom API base URL (for proxy services like Minimax)
        agent_type: Agent type for system prompt ("general-purpose", "explore", "plan")
        max_retries: Maximum retries for LLM rate limiting

    Returns:
        An async node function that processes messages through the LLM
    """

    async def reasoning_node(state: AgentState) -> dict:
        """Process the current state and generate a response.

        This node:
        1. Takes the current message history
        2. Injects Claude Code system prompt
        3. Calls the LLM with retry logic
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
        llm_api_base = base_url or os.environ.get("ANTHROPIC_BASE_URL", None)

        llm_kwargs = {
            "model": model_name,
            "anthropic_api_key": llm_api_key,
            "temperature": 1.0,  # Claude Code default
        }

        if llm_api_base:
            llm_kwargs["base_url"] = llm_api_base

        llm = ChatAnthropic(**llm_kwargs)

        # Get tool definitions for the LLM
        from tools.registry import get_tool_schemas

        tool_schemas = get_tool_schemas()

        # Bind tools using the dict schemas directly
        llm_with_tools = llm.bind_tools(tool_schemas)

        # Call the LLM with retry logic
        try:
            response = await call_llm_with_retry(
                llm_with_tools,
                all_messages,
                max_retries=max_retries,
            )
        except Exception as e:
            logger.error(f"LLM call failed after all retries: {e}")
            # Return error message instead of crashing
            return {
                "messages": [
                    AIMessage(
                        content=f"LLM call failed after retries: {str(e)[:200]}"
                    )
                ],
                "turn_count": turn_count + 1,
            }

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
