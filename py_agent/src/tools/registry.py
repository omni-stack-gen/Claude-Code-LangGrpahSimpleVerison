"""
Tool registry for Claude Code LangGraph Agent.

This module provides tool definitions in LangChain format.
"""
from typing import Any

from langchain_core.tools import BaseTool
from langchain_core.tools import tool as langchain_tool

from .client import ToolServerClient, RemoteTool


# Tool definitions mirroring Claude Code tools
# These are LangChain-format tool schemas that the LLM uses

BASH_TOOL_SCHEMA = {
    "name": "Bash",
    "description": "Execute shell commands in the sandbox. Use for running build tools, git, npm, python, etc. Returns the stdout and stderr output.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in seconds (default: 30)",
            },
        },
        "required": ["command"],
    },
}

GLOB_TOOL_SCHEMA = {
    "name": "Glob",
    "description": "Search for files by glob pattern. Use when you know the pattern but not the exact path.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern (e.g., '**/*.ts', 'src/**/*.js')",
            },
            "path": {
                "type": "string",
                "description": "Base path to search from (default: current directory)",
            },
        },
        "required": ["pattern"],
    },
}

GREP_TOOL_SCHEMA = {
    "name": "Grep",
    "description": "Search for text patterns in files using regex. Returns matching lines with context.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "Path to search in (default: current directory)",
            },
            "glob": {
                "type": "string",
                "description": "File glob to filter by (e.g., '*.ts')",
            },
            "context": {
                "type": "number",
                "description": "Number of context lines before and after",
            },
            "-i": {
                "type": "boolean",
                "description": "Case insensitive search",
            },
        },
        "required": ["pattern"],
    },
}

READ_TOOL_SCHEMA = {
    "name": "Read",
    "description": "Read the contents of a file. Returns the file contents as a string.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read",
            },
            "limit": {
                "type": "number",
                "description": "Maximum number of lines to read",
            },
            "offset": {
                "type": "number",
                "description": "Line offset to start from (0-indexed)",
            },
        },
        "required": ["file_path"],
    },
}

EDIT_TOOL_SCHEMA = {
    "name": "Edit",
    "description": "Make edits to an existing file by replacing exact text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "The exact string to replace (must match exactly, including whitespace)",
            },
            "new_string": {
                "type": "string",
                "description": "The replacement string",
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    },
}

WRITE_TOOL_SCHEMA = {
    "name": "Write",
    "description": "Create a new file or overwrite an existing file with content.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file",
            },
        },
        "required": ["file_path", "content"],
    },
}

AGENT_TOOL_SCHEMA = {
    "name": "Agent",
    "description": "Spawn a sub-agent to handle complex tasks. Use when a task requires deep exploration or specialized knowledge.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Description of the task for the sub-agent",
            },
            "agent_type": {
                "type": "string",
                "description": "Type of agent to use ('general-purpose', 'explore', or 'plan')",
            },
        },
        "required": ["task"],
    },
}

# Registry of all tool schemas
TOOL_SCHEMAS = [
    BASH_TOOL_SCHEMA,
    GLOB_TOOL_SCHEMA,
    GREP_TOOL_SCHEMA,
    READ_TOOL_SCHEMA,
    EDIT_TOOL_SCHEMA,
    WRITE_TOOL_SCHEMA,
    AGENT_TOOL_SCHEMA,
]

# Tool name to schema mapping
TOOL_NAME_TO_SCHEMA = {schema["name"]: schema for schema in TOOL_SCHEMAS}


def get_tool_schemas() -> list[dict[str, Any]]:
    """Get all tool schemas for the LLM.

    Returns:
        List of tool definition dicts in LangChain format
    """
    return TOOL_SCHEMAS


def get_tool_schema(tool_name: str) -> dict[str, Any] | None:
    """Get the schema for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        The tool schema dict, or None if not found
    """
    return TOOL_NAME_TO_SCHEMA.get(tool_name)


def create_remote_tool(
    tool_name: str,
    tool_server_url: str = "http://localhost:8080",
) -> RemoteTool | None:
    """Create a RemoteTool for a given tool name.

    Args:
        tool_name: Name of the tool
        tool_server_url: URL of the tool server

    Returns:
        A RemoteTool instance, or None if the tool is not found
    """
    schema = get_tool_schema(tool_name)
    if not schema:
        return None

    client = ToolServerClient(base_url=tool_server_url)
    return RemoteTool(client=client, tool_def=schema)


def get_all_remote_tools(
    tool_server_url: str = "http://localhost:8080",
) -> list[RemoteTool]:
    """Create RemoteTool instances for all known tools.

    Args:
        tool_server_url: URL of the tool server

    Returns:
        List of RemoteTool instances
    """
    client = ToolServerClient(base_url=tool_server_url)
    return [
        RemoteTool(client=client, tool_def=schema)
        for schema in TOOL_SCHEMAS
    ]
