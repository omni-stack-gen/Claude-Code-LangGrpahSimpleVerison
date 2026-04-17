"""
Tool server client for calling TypeScript tools from Python.
Includes retry logic with exponential backoff for transient errors.
"""
from __future__ import annotations

import httpx
import json
import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Retry configuration
DEFAULT_MAX_RETRIES = 5
DEFAULT_INITIAL_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 60.0  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {
    408,  # Request Timeout
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
    509,  # Bandwidth Limit Exceeded
    511,  # Network Authentication Required
    521,  # Web Server Is Down (Cloudflare)
    522,  # Connection Timed Out (Cloudflare)
    523,  # Origin Is Unreachable (Cloudflare)
    524,  # A Timeout Occurred (Cloudflare)
    525,  # SSL Handshake Failed (Cloudflare)
    526,  # Invalid SSL Certificate (Cloudflare)
    527,  # Railgun Error
    529,  # Overloaded (Minimax API)
}


def is_retryable_error(error: Exception) -> bool:
    """Check if an exception is retryable."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in RETRYABLE_STATUS_CODES
    if isinstance(error, httpx.TimeoutException):
        return True
    if isinstance(error, httpx.ConnectError):
        return True
    if isinstance(error, httpx.NetworkError):
        return True
    if isinstance(error, httpx.ProtocolError):
        return True
    if "529" in str(error):  # Overloaded error often in body
        return True
    if "overloaded_error" in str(error).lower():
        return True
    return False


def calculate_delay(attempt: int, initial_delay: float = DEFAULT_INITIAL_DELAY, multiplier: float = DEFAULT_BACKOFF_MULTIPLIER) -> float:
    """Calculate delay with exponential backoff and jitter."""
    import random
    delay = min(initial_delay * (multiplier ** attempt), DEFAULT_MAX_DELAY)
    # Add jitter (±10%)
    jitter = delay * 0.1 * (2 * random.random() - 1)
    return delay + jitter


async def call_with_retry(
    coro,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    on_retry: Optional[Callable] = None,
):
    """Execute an async coroutine with retry logic and exponential backoff.

    Args:
        coro: The async coroutine to execute
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        on_retry: Optional callback called with (attempt, error, delay) on each retry

    Returns:
        The result of the coroutine

    Raises:
        The last exception if all retries are exhausted
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return await coro
        except Exception as e:
            last_error = e

            if attempt >= max_retries:
                logger.warning(f"Max retries ({max_retries}) exhausted for {coro}")
                raise

            if not is_retryable_error(e):
                logger.debug(f"Non-retryable error: {e}")
                raise

            delay = calculate_delay(attempt, initial_delay)
            logger.warning(f"Retryable error on attempt {attempt + 1}/{max_retries + 1}: {e}")
            logger.info(f"Retrying in {delay:.1f}s...")

            if on_retry:
                on_retry(attempt + 1, e, delay)

            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    raise last_error


class ToolServerClient:
    """HTTP client for the TypeScript tool server with retry logic."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = 30.0,
    ):
        """Initialize the tool server client.

        Args:
            base_url: Base URL of the TypeScript tool server
            max_retries: Maximum number of retries for failed requests
            timeout: Default request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout

    def _log_retry(self, attempt: int, error: Exception, delay: float):
        """Callback for logging retries."""
        logger.warning(f"[Retry {attempt}] {type(error).__name__}: {str(error)[:100]}, waiting {delay:.1f}s")

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> dict:
        """Call a tool on the tool server with automatic retry.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            timeout: Request timeout in seconds (uses default if not specified)

        Returns:
            A dict with 'success', 'result', and optionally 'error' keys
        """
        url = f"{self.base_url}/tools/{tool_name}"
        timeout = timeout or self.timeout

        async def _make_request():
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

        try:
            return await call_with_retry(
                _make_request(),
                max_retries=self.max_retries,
                on_retry=self._log_retry,
            )
        except Exception as e:
            logger.error(f"Tool call failed after retries: {tool_name}: {e}")
            return {
                "success": False,
                "error": f"Tool call failed: {str(e)}",
            }

    def call_tool_sync(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> dict:
        """Synchronously call a tool on the tool server (with retries).

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            timeout: Request timeout in seconds (uses default if not specified)

        Returns:
            A dict with 'success', 'result', and optionally 'error' keys
        """
        url = f"{self.base_url}/tools/{tool_name}"
        timeout = timeout or self.timeout
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
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

            except Exception as e:
                last_error = e

                if attempt >= self.max_retries:
                    break

                if not is_retryable_error(e):
                    break

                import time
                delay = calculate_delay(attempt)
                logger.warning(f"[Retry {attempt + 1}] {type(e).__name__}: {str(e)[:100]}, waiting {delay:.1f}s")
                time.sleep(delay)

        return {
            "success": False,
            "error": f"Tool call failed: {str(last_error)}",
        }

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
