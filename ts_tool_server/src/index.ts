/**
 * Claude Code Tool Server
 *
 * HTTP server that exposes Claude Code tools for consumption by
 * Python LangGraph agents via JSON RPC over HTTP.
 *
 * Usage:
 *   npm run dev    # Development mode with tsx
 *   npm run build  # Compile TypeScript
 *   npm start      # Production mode
 */

import { startServer } from './tools/server.js';

const PORT = parseInt(process.env.PORT || '8080', 10);

console.log('Starting Claude Code Tool Server...');
console.log(`Port: ${PORT}`);
console.log('');

startServer(PORT).catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});
