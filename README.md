# Claude Code LangGraph Agent

A Python [LangGraph](https://github.com/langchain-ai/langgraph)-based agent that reuses Claude Code's tool implementations via a TypeScript tool server bridge.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Python LangGraph Agent (py_agent/)                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │  StateGraph                                       │   │
│  │    ├── reasoning_node (LLM call via Anthropic)   │   │
│  │    └── tools_node (tool execution via HTTP)      │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓ JSON over HTTP               │
│  ┌─────────────────────────────────────────────────┐   │
│  │  TypeScript Tool Server (ts_tool_server/)        │   │
│  │    - Express HTTP server                         │   │
│  │    - Tool implementations (Bash, Glob, Grep...) │   │
│  │    - Sandbox integration (bubblewrap)            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Features

- **LangGraph StateGraph**: Structured agent loop with reasoning → tool execution → reasoning cycle
- **Claude Code Prompts**: Real prompts extracted from Claude Code source (`src/constants/prompts.ts`)
- **7 Tools**: Bash, Glob, Grep, Read, Edit, Write, Agent (sub-agent spawning)
- **3 Agent Types**: `general-purpose`, `explore`, `plan`
- **Async Native**: Full async/await support via `ainvoke()` and `astream()`
- **Sandbox Ready**: bubblewrap integration on Linux for filesystem isolation
- **Tool Bridge**: HTTP-based IPC between Python agent and TypeScript tools

## Project Structure

```
claude_langgraph_agent/
├── py_agent/                      # Python LangGraph Agent
│   ├── src/
│   │   ├── agent/                 # Core agent
│   │   │   ├── graph.py           # StateGraph + ClaudeCodeAgent class
│   │   │   ├── state.py           # AgentState TypedDict
│   │   │   ├── nodes/
│   │   │   │   ├── reasoning.py   # LLM reasoning node
│   │   │   │   └── tools.py       # Tool execution node
│   │   │   └── prompts/
│   │   │       └── system.py      # Claude Code prompts
│   │   ├── tools/
│   │   │   ├── client.py          # HTTP client for tool server
│   │   │   └── registry.py        # Tool schemas (LangChain format)
│   │   └── sandbox/
│   │       └── config.py          # Sandbox configuration
│   ├── tests/                     # 18 passing tests
│   ├── demo.py                   # End-to-end demo
│   └── pyproject.toml
│
├── ts_tool_server/               # TypeScript Tool Server
│   ├── src/
│   │   ├── index.ts              # Entry point
│   │   ├── tools/
│   │   │   ├── server.ts         # Express HTTP server
│   │   │   ├── executor.ts        # Tool execution logic
│   │   │   ├── ripgrep.ts        # Grep implementation
│   │   │   └── types.ts          # TypeScript types
│   │   └── sandbox/
│   │       └── executor.ts        # bubblewrap sandbox
│   ├── dist/                     # Compiled JavaScript
│   └── package.json
│
└── prompts/                      # Extracted Claude Code prompts
    └── README.md
```

## Quick Start

### 1. Environment Setup

```bash
# Create conda environment
conda create -y -n claude_langgraph python=3.11
conda activate claude_langgraph

# Install Python dependencies
cd py_agent
pip install -e .

# Install TypeScript dependencies
cd ../ts_tool_server
npm install
```

### 2. Start the Tool Server

```bash
cd ts_tool_server
npm run dev
# Server listening on http://localhost:8080
```

### 3. Run the Agent

```bash
conda activate claude_langgraph
cd py_agent

export ANTHROPIC_API_KEY=sk-xxx-xxxx
python demo.py
```

Or programmatically:

```python
from agent import ClaudeCodeAgent

agent = ClaudeCodeAgent(
    model_name="claude-opus-4-6",
    tool_server_url="http://localhost:8080",
)

result = agent.run("List all Python files in src/ using Glob")
print(result)
```

## Agent Usage

### Synchronous

```python
from agent import ClaudeCodeAgent

agent = ClaudeCodeAgent(
    model_name="claude-opus-4-6",
    tool_server_url="http://localhost:8080",
    max_turns=50,
)

result = agent.run("Your task here")
print(result["messages"])
```

### Async

```python
import asyncio
from agent import ClaudeCodeAgent

async def main():
    agent = ClaudeCodeAgent(tool_server_url="http://localhost:8080")
    result = await agent.run_async("Your task here")
    print(result)

asyncio.run(main())
```

### Streaming

```python
for chunk in agent.run_stream("Your task here"):
    print(chunk)
```

## Tool Server API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/tools` | List all tools |
| GET | `/tools/:name` | Get tool definition |
| POST | `/tools/:name` | Execute tool |

### Execute a Tool

```bash
curl -X POST http://localhost:8080/tools/Bash \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"command": "echo hello"}}'
```

Response:
```json
{
  "success": true,
  "result": {
    "stdout": "hello\n",
    "stderr": "",
    "exitCode": 0
  }
}
```

## Tools Available

| Tool | Description |
|------|-------------|
| `Bash` | Execute shell commands |
| `Glob` | Search files by glob pattern |
| `Grep` | Search text patterns (regex) |
| `Read` | Read file contents |
| `Edit` | Edit existing files (replace exact text) |
| `Write` | Create/overwrite files |
| `Agent` | Spawn sub-agents |

## Sandbox Configuration

```python
from sandbox import create_restricted_sandbox_config

config = create_restricted_sandbox_config(
    allowed_directories=["/home/user/project"],
    denied_directories=["/etc", "/var", "/sys"],
)

agent = ClaudeCodeAgent(
    sandbox_config=config,
)
```

## Testing

```bash
cd py_agent
pytest tests/ -v
# 18 passed
```

## Development

### TypeScript Compilation

```bash
cd ts_tool_server
npm run build
```

### Run Demo

```bash
cd py_agent
python demo.py
```

## Key Design Decisions

1. **HTTP Bridge**: Python and TypeScript run in separate processes, communicating over HTTP. This avoids GIL issues and allows independent scaling.

2. **Async-First**: All tool calls are async (`ainvoke`), enabling true parallelism in the LangGraph loop.

3. **Claude Code Prompts**: Real prompts extracted from `src/constants/prompts.ts` — not placeholders. The agent behaves consistently with Claude Code.

4. **LangGraph StateGraph**: Uses `add_messages` reducer for automatic message list management, with conditional edges for tool call routing.

5. **Bubblewrap Sandbox**: On Linux, commands can be wrapped with bubblewrap for filesystem isolation. Falls back to direct execution on macOS.

## License

MIT
