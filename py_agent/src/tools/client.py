"""
Tool server client for calling TypeScript tools from Python.
"""
import httpx
import json
from typing import Any


class ToolServerClient:
    """HTTP client for the TypeScript tool server."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        """Initialize the tool server client.

        Args:
            base_url: Base URL of the TypeScript tool server
        """
        self.base_url = base_url.rstrip("/")

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict:
        """Call a tool on the tool server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            timeout: Request timeout in seconds

        Returns:
            A dict with 'success', 'result', and optionally 'error' keys
        """
        url = f"{self.base_url}/tools/{tool_name}"

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json={"arguments": arguments},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found",
                }

            response.raise_for_status()
            return response.json()

    def call_tool_sync(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict:
        """Synchronously call a tool on the tool server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            timeout: Request timeout in seconds

        Returns:
            A dict with 'success', 'result', and optionally 'error' keys
        """
        url = f"{self.base_url}/tools/{tool_name}"

        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                json={"arguments": arguments},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found",
                }

            response.raise_for_status()
            return response.json()

    async def list_tools(self) -> list[dict]:
        """List all available tools.

        Returns:
            A list of tool definition dicts
        """
        url = f"{self.base_url}/tools"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("tools", [])

    async def get_tool_definition(self, tool_name: str) -> dict | None:
        """Get the definition for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            The tool definition dict, or None if not found
        """
        url = f"{self.base_url}/tools/{tool_name}/definition"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                return None


class RemoteTool:
    """A LangChain tool that wraps a remote tool server tool.

    This class adapts the TypeScript tool server tools to work
    with LangChain's tool interface.
    """

    def __init__(self, client: ToolServerClient, tool_def: dict):
        """Initialize a remote tool.

        Args:
            client: The tool server client to use
            tool_def: The tool definition from the server
        """
        self.client = client
        self.name = tool_def.get("name", "unknown")
        self.description = tool_def.get("description", "")
        self.input_schema = tool_def.get("input_schema", {})
        self.tool_def = tool_def

    @property
    def args_schema(self) -> type:
        """Return the input schema as a Pydantic type."""
        from pydantic import BaseModel, Field

        properties = self.input_schema.get("properties", {})
        schema_fields = {}
        for name, spec in properties.items():
            field_type = spec.get("type", "string")
            description = spec.get("description", "")
            schema_fields[name] = Field(description=description)

        return BaseModel, {"model": BaseModel, "schema_fields": schema_fields}

    def invoke(self, input_data: dict | str) -> str:
        """Invoke the tool with the given input.

        Args:
            input_data: Either a dict of arguments or a JSON string

        Returns:
            The tool result as a string
        """
        if isinstance(input_data, str):
            input_data = json.loads(input_data)

        result = self.client.call_tool_sync(self.name, input_data)

        if result.get("success"):
            return json.dumps(result.get("result", ""))
        else:
            error = result.get("error", "Unknown error")
            return json.dumps({"error": error})

    async def ainvoke(self, input_data: dict | str) -> str:
        """Async invoke the tool with the given input.

        Args:
            input_data: Either a dict of arguments or a JSON string

        Returns:
            The tool result as a string
        """
        if isinstance(input_data, str):
            input_data = json.loads(input_data)

        result = await self.client.call_tool(self.name, input_data)

        if result.get("success"):
            return json.dumps(result.get("result", ""))
        else:
            error = result.get("error", "Unknown error")
            return json.dumps({"error": error})
