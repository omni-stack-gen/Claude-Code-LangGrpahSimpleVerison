/**
 * Sandbox Executor
 *
 * Simplified sandbox executor that bridges to the Claude Code sandbox.
 * This reuses the sandbox-adapter.ts interface from Claude Code.
 */

import { execSync, execFileSync } from 'child_process';
import { SandboxConfig } from '../tools/types.js';

/**
 * Execute a command in a sandboxed environment.
 *
 * This is a simplified implementation that wraps commands with
 * bubblewrap on Linux or just runs them directly on macOS.
 *
 * For full sandbox integration, this should be replaced with the
 * actual sandbox-adapter.ts implementation from Claude Code.
 */
export async function executeSandboxed(
  command: string,
  config?: SandboxConfig,
  abortSignal?: AbortSignal
): Promise<string> {
  // If no sandbox config, run directly
  if (!config || !config.filesystem) {
    return executeDirect(command);
  }

  // Check platform
  const platform = process.platform;

  if (platform === 'linux') {
    return executeWithBubblewrap(command, config);
  } else if (platform === 'darwin') {
    // macOS: sandboxing is more limited, run with possible restrictions
    return executeDirect(command);
  } else {
    // Unsupported platform, run directly with warning
    console.warn(`Sandbox not supported on ${platform}, running without sandbox`);
    return executeDirect(command);
  }
}

function executeDirect(command: string): string {
  try {
    const output = execSync(command, {
      encoding: 'utf-8',
      maxBuffer: 50 * 1024 * 1024, // 50MB
    });
    return output;
  } catch (error) {
    if (error && typeof error === 'object' && 'stdout' in error) {
      const execError = error as { stdout: unknown; stderr: unknown; status: number };
      return `stdout: ${String(execError.stdout)}\nstderr: ${String(execError.stderr)}\nexit code: ${execError.status}`;
    }
    throw error;
  }
}

function executeWithBubblewrap(command: string, config: SandboxConfig): string {
  const args: string[] = [];

  // Filesystem restrictions
  const fs = config.filesystem;
  if (fs) {
    // Deny read paths
    for (const path of fs.denyRead || []) {
      args.push('--ro-bind-try', path, path);
    }

    // Allow read paths
    for (const path of fs.allowRead || []) {
      args.push('--ro-bind', path, path);
    }

    // Allow write paths
    for (const path of fs.allowWrite || []) {
      args.push('--bind', path, path);
    }

    // Deny write paths
    for (const path of fs.denyWrite || []) {
      args.push('--bind-try', path, path);
    }
  }

  // Network restrictions (simplified)
  const net = config.network;
  if (net) {
    if (!net.allowUnixSockets) {
      args.push('--unshare-net');
    }
  }

  // Add the command
  args.push('--');
  args.push('sh', '-c', command);

  try {
    const bwrapPath = findBubblewrap();
    if (!bwrapPath) {
      console.warn('bubblewrap not found, running without sandbox');
      return executeDirect(command);
    }

    // execFileSync: first arg is file, second is args array, third is options
    const output = execFileSync(bwrapPath, args, {
      encoding: 'utf-8',
      maxBuffer: 50 * 1024 * 1024,
    });
    return output;
  } catch (error) {
    if (error && typeof error === 'object' && 'stdout' in error) {
      const execError = error as { stdout: unknown; stderr: unknown; status: number };
      return `stdout: ${String(execError.stdout)}\nstderr: ${String(execError.stderr)}\nexit code: ${execError.status}`;
    }
    throw error;
  }
}

function findBubblewrap(): string | null {
  const paths = [
    '/usr/bin/bwrap',
    '/usr/local/bin/bwrap',
    '/bin/bwrap',
  ];

  for (const path of paths) {
    try {
      execSync(`test -x ${path}`, { stdio: 'ignore' });
      return path;
    } catch {
      // Not found at this path
    }
  }

  return null;
}

/**
 * Check if sandboxing is supported on this platform.
 */
export function isSandboxSupported(): boolean {
  const platform = process.platform;
  if (platform === 'linux') {
    return findBubblewrap() !== null;
  }
  // macOS and others - partial support
  return true;
}

/**
 * Get the sandbox unavailable reason if any.
 */
export function getSandboxUnavailableReason(): string | undefined {
  const platform = process.platform;

  if (platform === 'win32') {
    return 'Sandbox is not supported on Windows';
  }

  if (platform === 'linux' && !findBubblewrap()) {
    return 'bubblewrap is not installed. Install it with: apt install bubblewrap';
  }

  return undefined;
}
