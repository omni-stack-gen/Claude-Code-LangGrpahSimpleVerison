# Claude Code Prompts

This directory contains system prompts extracted from Claude Code for use in the LangGraph agent implementation.

## Source Files

The prompts are extracted from these Claude Code source files:

| Source File | Purpose |
|------------|---------|
| `src/tools/AgentTool/built-in/generalPurposeAgent.ts` | General purpose agent prompt |
| `src/tools/AgentTool/built-in/exploreAgent.ts` | Explore agent prompt |
| `src/tools/AgentTool/built-in/planAgent.ts` | Plan agent prompt |

## Prompt Types

### General Purpose Agent
The default agent type for most tasks. Strong at:
- Searching for code, configurations, and patterns
- Analyzing file structures and architecture
- Multi-step research tasks
- File editing and creation

### Explore Agent
Specialized for discovery and mapping tasks:
- Understanding unknown codebases
- Finding patterns and relationships
- File structure exploration

### Plan Agent
Specialized for planning and breaking down tasks:
- Task decomposition
- Milestone planning
- Dependency identification

## Usage

```python
from agent.prompts.system import get_system_prompt

# Get prompt for a specific agent type
prompt = get_system_prompt("general-purpose")
```

## Prompt Guidelines

Guidelines shared across all agent types:
- Be thorough but efficient
- Search broadly when unsure
- Prefer editing to creating new files
- Never create documentation unless explicitly requested
