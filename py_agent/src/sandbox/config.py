"""
Sandbox configuration types and utilities.

This module provides types and utilities for sandbox configuration,
extracted from the Claude Code sandbox-adapter.ts for use in the Python agent.
"""
from typing import TypedDict


class NetworkConfig(TypedDict, total=False):
    """Network configuration for the sandbox."""
    allowedDomains: list[str]
    deniedDomains: list[str]
    allowUnixSockets: bool | None
    allowAllUnixSockets: bool | None
    allowLocalBinding: bool | None
    httpProxyPort: int | None
    socksProxyPort: int | None


class FilesystemConfig(TypedDict, total=False):
    """Filesystem configuration for the sandbox."""
    denyRead: list[str]
    allowRead: list[str]
    allowWrite: list[str]
    denyWrite: list[str]


class RipgrepConfig(TypedDict, total=False):
    """Ripgrep configuration for the sandbox."""
    command: str
    args: list[str]
    argv0: str | None


class SandboxConfig(TypedDict, total=False):
    """Complete sandbox configuration."""
    network: NetworkConfig | None
    filesystem: FilesystemConfig | None
    ignoreViolations: bool | None
    enableWeakerNestedSandbox: bool | None
    enableWeakerNetworkIsolation: bool | None
    ripgrep: RipgrepConfig | None


def get_default_sandbox_config() -> SandboxConfig:
    """Get the default sandbox configuration.

    Returns:
        A SandboxConfig with sensible defaults
    """
    return SandboxConfig(
        network=NetworkConfig(
            allowedDomains=[],
            deniedDomains=[],
            allowUnixSockets=None,
            allowAllUnixSockets=None,
            allowLocalBinding=None,
            httpProxyPort=None,
            socksProxyPort=None,
        ),
        filesystem=FilesystemConfig(
            denyRead=[],
            allowRead=[],
            allowWrite=["."],  # Current directory
            denyWrite=[],
        ),
        ignoreViolations=None,
        enableWeakerNestedSandbox=None,
        enableWeakerNetworkIsolation=None,
        ripgrep=None,
    )


def create_restricted_sandbox_config(
    allowed_directories: list[str],
    denied_directories: list[str] | None = None,
) -> SandboxConfig:
    """Create a sandbox config with restricted filesystem access.

    Args:
        allowed_directories: List of directories the agent can access
        denied_directories: Optional list of directories to explicitly deny

    Returns:
        A SandboxConfig with restricted access
    """
    denied = denied_directories or []

    return SandboxConfig(
        filesystem=FilesystemConfig(
            denyRead=denied,
            allowRead=allowed_directories,
            allowWrite=allowed_directories,
            denyWrite=denied,
        ),
    )
