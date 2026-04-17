/**
 * Simple grep implementation using ripgrep.
 */

import { execFileSync } from 'child_process';
import { join } from 'path';

export interface GrepMatch {
  file: string;
  line: number;
  content: string;
}

export interface GrepOptions {
  glob?: string;
  context?: number;
  caseInsensitive?: boolean;
}

export function grepSync(
  pattern: string,
  path: string,
  options: GrepOptions = {}
): { matches: GrepMatch[]; total: number } {
  const { glob, context = 0, caseInsensitive = false } = options;

  // Build rg arguments
  const rgArgs = [
    '--hidden', // Include hidden files
    '--no-ignore', // Don't respect .gitignore
    '--json', // Output JSON for easier parsing
  ];

  if (context > 0) {
    rgArgs.push(`-${context}`);
    rgArgs.push(`-${context}`);
  }

  if (caseInsensitive) {
    rgArgs.push('-i');
  }

  if (glob) {
    rgArgs.push('--glob', glob);
  }

  rgArgs.push(pattern);
  rgArgs.push(path);

  try {
    // Try to find ripgrep
    const rgPath = process.env.RG_PATH || 'rg';

    const output = execFileSync(rgPath, rgArgs, {
      encoding: 'utf-8',
      cwd: path,
      maxBuffer: 50 * 1024 * 1024, // 50MB
    });

    const matches: GrepMatch[] = [];
    let lineIndex = 0;

    // Parse JSON output from ripgrep
    for (const line of output.split('\n')) {
      if (!line.trim()) continue;

      try {
        const parsed = JSON.parse(line);

        if (parsed.type === 'match') {
          const data = parsed.data;
          const result = data.substitutions?.[0]?.text || data.lines?.text || '';

          matches.push({
            file: data.path?.text || '',
            line: data.line_number || ++lineIndex,
            content: result,
          });
        } else if (parsed.type === 'context') {
          const data = parsed.data;
          lineIndex = data.line_number || lineIndex;
        }
      } catch {
        // Skip unparseable lines
      }
    }

    return { matches, total: matches.length };
  } catch (error) {
    // If ripgrep is not available, return empty results
    if (error instanceof Error && error.message.includes('ENOENT')) {
      console.warn('ripgrep (rg) not found. Install ripgrep for grep functionality.');
      return { matches: [], total: 0 };
    }
    throw error;
  }
}
