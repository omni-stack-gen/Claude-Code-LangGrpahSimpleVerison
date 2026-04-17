/**
 * Tool Executor - bridges to Claude Code tools.
 *
 * This module provides the execution logic for tools, reusing the
 * tool implementations from Claude Code where possible.
 */

import { ToolDefinition, SandboxConfig } from './types.js';

// Re-export sandbox types for use in the tool server
export type { SandboxConfig } from './types.js';

// ============================================================================
// Tool Definitions
// ============================================================================

const TOOL_DEFINITIONS: ToolDefinition[] = [
  {
    name: 'Bash',
    description: 'Execute shell commands in the sandbox. Use for running build tools, git, npm, python, etc. Returns the stdout and stderr output.',
    input_schema: {
      type: 'object',
      properties: {
        command: {
          type: 'string',
          description: 'The shell command to execute',
        },
        timeout: {
          type: 'number',
          description: 'Timeout in seconds (default: 30)',
        },
      },
      required: ['command'],
    },
  },
  {
    name: 'Glob',
    description: 'Search for files by glob pattern. Use when you know the pattern but not the exact path.',
    input_schema: {
      type: 'object',
      properties: {
        pattern: {
          type: 'string',
          description: "Glob pattern (e.g., '**/*.ts', 'src/**/*.js')",
        },
        path: {
          type: 'string',
          description: 'Base path to search from (default: current directory)',
        },
      },
      required: ['pattern'],
    },
  },
  {
    name: 'Grep',
    description: 'Search for text patterns in files using regex. Returns matching lines with context.',
    input_schema: {
      type: 'object',
      properties: {
        pattern: {
          type: 'string',
          description: 'Regex pattern to search for',
        },
        path: {
          type: 'string',
          description: 'Path to search in (default: current directory)',
        },
        glob: {
          type: 'string',
          description: "File glob to filter by (e.g., '*.ts')",
        },
        context: {
          type: 'number',
          description: 'Number of context lines before and after',
        },
        '-i': {
          type: 'boolean',
          description: 'Case insensitive search',
        },
      },
      required: ['pattern'],
    },
  },
  {
    name: 'Read',
    description: 'Read the contents of a file. Returns the file contents as a string.',
    input_schema: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Path to the file to read',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of lines to read',
        },
        offset: {
          type: 'number',
          description: 'Line offset to start from (0-indexed)',
        },
      },
      required: ['file_path'],
    },
  },
  {
    name: 'Edit',
    description: 'Make edits to an existing file by replacing exact text.',
    input_schema: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Path to the file to edit',
        },
        old_string: {
          type: 'string',
          description: 'The exact string to replace (must match exactly, including whitespace)',
        },
        new_string: {
          type: 'string',
          description: 'The replacement string',
        },
      },
      required: ['file_path', 'old_string', 'new_string'],
    },
  },
  {
    name: 'Write',
    description: 'Create a new file or overwrite an existing file with content.',
    input_schema: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Path to the file to write',
        },
        content: {
          type: 'string',
          description: 'The content to write to the file',
        },
      },
      required: ['file_path', 'content'],
    },
  },
  {
    name: 'Agent',
    description: 'Spawn a sub-agent to handle complex tasks. Use when a task requires deep exploration or specialized knowledge.',
    input_schema: {
      type: 'object',
      properties: {
        task: {
          type: 'string',
          description: 'Description of the task for the sub-agent',
        },
        agent_type: {
          type: 'string',
          description: "Type of agent to use ('general-purpose', 'explore', or 'plan')",
        },
      },
      required: ['task'],
    },
  },
];

// Tool name to definition mapping
const TOOL_MAP = new Map<string, ToolDefinition>(
  TOOL_DEFINITIONS.map((def) => [def.name, def])
);

// ============================================================================
// Tool Registry Functions
// ============================================================================

/**
 * Get all tool definitions.
 */
export function getAllToolDefinitions(): ToolDefinition[] {
  return TOOL_DEFINITIONS;
}

/**
 * Get the definition for a specific tool.
 */
export function getToolDefinition(toolName: string): ToolDefinition | undefined {
  return TOOL_MAP.get(toolName);
}

// ============================================================================
// Tool Implementations
// ============================================================================

// Import Node.js built-ins for tool implementations
import { readFile, writeFile, stat, readdir } from 'fs/promises';
import { execSync } from 'child_process';
import { join, relative, isAbsolute } from 'path';
import { glob as globSync } from 'glob';
import { grepSync } from './ripgrep.js';

/**
 * Execute a tool by name with the given arguments.
 */
export async function executeTool(
  toolName: string,
  args: Record<string, unknown>,
  _sandboxConfig?: SandboxConfig
): Promise<unknown> {
  switch (toolName) {
    case 'Bash':
      return executeBash(args);
    case 'Glob':
      return executeGlob(args);
    case 'Grep':
      return executeGrep(args);
    case 'Read':
      return executeRead(args);
    case 'Edit':
      return executeEdit(args);
    case 'Write':
      return executeWrite(args);
    case 'Agent':
      return executeAgent(args);
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

// ============================================================================
// Tool Execution Functions
// ============================================================================

function executeBash(args: Record<string, unknown>): { stdout: string; stderr: string; exitCode: number } {
  const command = args.command as string;
  const timeout = (args.timeout as number) || 30;

  if (!command) {
    throw new Error('Bash tool requires a "command" argument');
  }

  try {
    const options = {
      encoding: 'utf-8' as const,
      timeout: timeout * 1000, // Convert to ms
      maxBuffer: 10 * 1024 * 1024, // 10MB
    };

    const stdout = execSync(command, options).toString();
    return { stdout, stderr: '', exitCode: 0 };
  } catch (error: unknown) {
    if (error && typeof error === 'object' && 'status' in error) {
      const execError = error as { status: number; stdout?: string; stderr?: string };
      return {
        stdout: execError.stdout?.toString() || '',
        stderr: execError.stderr?.toString() || '',
        exitCode: execError.status,
      };
    }
    throw error;
  }
}

async function executeGlob(args: Record<string, unknown>): Promise<string[]> {
  const pattern = args.pattern as string;
  const basePath = (args.path as string) || process.cwd();

  if (!pattern) {
    throw new Error('Glob tool requires a "pattern" argument');
  }

  // Resolve relative paths
  const searchPath = isAbsolute(pattern) ? pattern : join(basePath, pattern);

  try {
    const files = await globSync(searchPath, {
      cwd: basePath,
      absolute: false,
    });
    return files;
  } catch (error) {
    console.error('Glob error:', error);
    return [];
  }
}

function executeGrep(args: Record<string, unknown>): { matches: GrepMatch[]; total: number } {
  const pattern = args.pattern as string;
  const path = (args.path as string) || process.cwd();
  const glob = args.glob as string | undefined;
  const context = (args.context as number) || 0;
  const caseInsensitive = args['-i'] as boolean | undefined;

  if (!pattern) {
    throw new Error('Grep tool requires a "pattern" argument');
  }

  try {
    const results = grepSync(pattern, path, {
      glob,
      context,
      caseInsensitive,
    });
    return results;
  } catch (error) {
    console.error('Grep error:', error);
    return { matches: [], total: 0 };
  }
}

interface GrepMatch {
  file: string;
  line: number;
  content: string;
}

async function executeRead(args: Record<string, unknown>): Promise<string> {
  const filePath = args.file_path as string;
  const limit = args.limit as number | undefined;
  const offset = args.offset as number | undefined;

  if (!filePath) {
    throw new Error('Read tool requires a "file_path" argument');
  }

  const content = await readFile(filePath, 'utf-8');

  // Apply offset and limit
  let lines = content.split('\n');
  if (offset !== undefined) {
    lines = lines.slice(offset);
  }
  if (limit !== undefined) {
    lines = lines.slice(0, limit);
  }

  return lines.join('\n');
}

async function executeEdit(args: Record<string, unknown>): Promise<{ success: boolean; changes: string }> {
  const filePath = args.file_path as string;
  const oldString = args.old_string as string;
  const newString = args.new_string as string;

  if (!filePath || !oldString || newString === undefined) {
    throw new Error('Edit tool requires "file_path", "old_string", and "new_string" arguments');
  }

  const content = await readFile(filePath, 'utf-8');

  if (!content.includes(oldString)) {
    throw new Error(`Could not find old_string in file: ${filePath}`);
  }

  const newContent = content.replace(oldString, newString);
  await writeFile(filePath, newContent, 'utf-8');

  return { success: true, changes: `Replaced "${oldString}" with "${newString}"` };
}

async function executeWrite(args: Record<string, unknown>): Promise<{ success: boolean; path: string }> {
  const filePath = args.file_path as string;
  const content = args.content as string;

  if (!filePath || content === undefined) {
    throw new Error('Write tool requires "file_path" and "content" arguments');
  }

  await writeFile(filePath, content, 'utf-8');

  return { success: true, path: filePath };
}

function executeAgent(args: Record<string, unknown>): { task: string; agent_type: string; status: string } {
  const task = args.task as string;
  const agentType = (args.agent_type as string) || 'general-purpose';

  if (!task) {
    throw new Error('Agent tool requires a "task" argument');
  }

  // In a full implementation, this would spawn a sub-agent
  // For now, return a placeholder response
  return {
    task,
    agent_type: agentType,
    status: 'subagent_spawned',
  };
}
