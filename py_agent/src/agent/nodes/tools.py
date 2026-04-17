"""
Tools node for LangGraph - executes tool calls.
"""
import json
from typing import Any

from agent.state import AgentState
from tools.client import ToolServerClient


def create_tools_node(
    tool_server_url: str = "http://localhost:8080",
):
    """Create a tools node that executes tool calls via the TS tool server.

    Args:
        tool_server_url: URL of the TypeScript tool server

    Returns:
        A node function that executes tool calls
    """

    async def tools_node_async(state: AgentState) -> dict:
        """Execute tool calls from the last message.

        This node:
        1. Extracts tool calls from the last AI message
        2. Calls the tool server to execute each tool
        3. Returns the results as tool result messages
        """
        from langchain_core.messages import AIMessage, ToolMessage

        messages = state["messages"]
        tool_results = list(state["tool_results"])

        if not messages:
            return {"tool_results": tool_results}

        last_message = messages[-1]

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"tool_results": tool_results}

        # Create tool server client
        client = ToolServerClient(base_url=tool_server_url)

        # Execute each tool call
        new_messages = []
        for tool_call in last_message.tool_calls:
            # Handle both ToolCall objects (LangChain) and dicts (some API providers)
            tool_name = tool_call.name if hasattr(tool_call, 'name') else tool_call.get('name')
            tool_args = tool_call.args if hasattr(tool_call, 'args') else tool_call.get('args')

            try:
                # Call the tool server
                result = await client.call_tool(tool_name, tool_args)

                # Create a ToolMessage with the result
                if result.get("success"):
                    content = json.dumps(result.get("result", ""))
                else:
                    content = json.dumps({"error": result.get("error", "Unknown error")})

                tool_message = ToolMessage(
                    content=content,
                    tool_call_id=tool_call.id if hasattr(tool_call, 'id') else tool_call.get('id'),
                    name=tool_name,
                )
                new_messages.append(tool_message)

                # Store the tool result
                tool_results.append({
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "result": result,
                })

            except Exception as e:
                # Handle connection errors
                error_message = ToolMessage(
                    content=json.dumps({"error": f"Tool server error: {str(e)}"}),
                    tool_call_id=tool_call.id if hasattr(tool_call, 'id') else tool_call.get('id'),
                    name=tool_name,
                )
                new_messages.append(error_message)

                tool_results.append({
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "result": None,
                    "error": str(e),
                })

        return {
            "messages": new_messages,
            "tool_results": tool_results,
        }

    # Return the async version for use with ainvoke()
    return tools_node_async
