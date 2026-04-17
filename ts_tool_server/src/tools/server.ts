/**
 * TypeScript Tool Server
 *
 * HTTP server that exposes Claude Code tools for consumption by the
 * Python LangGraph agent via JSON RPC over HTTP.
 */

import express, { Request, Response, NextFunction } from 'express';
import { ToolCallRequest, ToolCallResponse, ToolDefinition } from './types.js';
import { executeTool, getAllToolDefinitions, getToolDefinition } from './executor.js';

const app = express();
const PORT = Number(process.env.PORT) || 8080;

// Middleware
app.use(express.json());

// Request logging middleware
app.use((req: Request, _res: Response, next: NextFunction) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// Health check endpoint
app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// List all available tools
app.get('/tools', (_req: Request, res: Response) => {
  try {
    const tools = getAllToolDefinitions();
    res.json({ tools });
  } catch (error) {
    console.error('Error listing tools:', error);
    res.status(500).json({ error: String(error) });
  }
});

// Get definition for a specific tool
app.get('/tools/:toolName/definition', (req: Request, res: Response) => {
  const { toolName } = req.params;

  try {
    const definition = getToolDefinition(toolName);
    if (!definition) {
      res.status(404).json({ error: `Tool '${toolName}' not found` });
      return;
    }
    res.json(definition);
  } catch (error) {
    console.error(`Error getting tool definition for '${toolName}':`, error);
    res.status(500).json({ error: String(error) });
  }
});

// Execute a tool
app.post('/tools/:toolName', async (req: Request, res: Response) => {
  const { toolName } = req.params;
  const { arguments: args = {}, sandbox_config: sandboxConfig } = req.body as ToolCallRequest;

  console.log(`[Tool Call] ${toolName}`, { args });

  try {
    const result = await executeTool(toolName, args, sandboxConfig);

    const response: ToolCallResponse = {
      success: true,
      result,
    };

    res.json(response);
  } catch (error) {
    console.error(`[Tool Error] ${toolName}:`, error);

    const response: ToolCallResponse = {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    };

    res.json(response);
  }
});

// Error handling middleware
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: err.message || 'Internal server error' });
});

// Start the server
function startServer(port: number = PORT): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      app.listen(port, () => {
        console.log(`Claude Tool Server listening on port ${port}`);
        console.log(`Health check: http://localhost:${port}/health`);
        console.log(`Tools list: http://localhost:${port}/tools`);
        resolve();
      });
    } catch (error) {
      reject(error);
    }
  });
}

export { app, startServer };
