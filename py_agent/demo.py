#!/usr/bin/env python3
"""
Claude Code LangGraph Agent - End-to-End Demo

This script demonstrates the complete agent loop:
1. Start TS Tool Server (background)
2. Create ClaudeCodeAgent
3. Run agent with a simple task
4. Observe the reasoning → tools → reasoning loop

Usage:
    # Terminal 1: Start tool server
    cd ts_tool_server && npm run dev

    # Terminal 2: Run demo
    cd py_agent && python demo.py
"""
import asyncio
import os

# Set up paths
import sys
sys.path.insert(0, 'src')

from agent import ClaudeCodeAgent


async def demo_agent_loop():
    """Demonstrate the agent loop with a simple task."""

    print("=" * 70)
    print("Claude Code LangGraph Agent - End-to-End Demo")
    print("=" * 70)
    print()

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set - will use mock mode for demo")
        print("   Set it with: export ANTHROPIC_API_KEY=your_key")
        print()

    # Create agent
    agent = ClaudeCodeAgent(
        model_name="claude-opus-4-6",
        tool_server_url="http://localhost:8080",
        api_key=api_key,
        max_turns=5,
        agent_type="general-purpose",
    )

    print(f"Agent config:")
    print(f"  model: {agent.model_name}")
    print(f"  tool_server: {agent.tool_server_url}")
    print(f"  max_turns: {agent.max_turns}")
    print(f"  agent_type: {agent.agent_type}")
    print()

    # Simple task that should trigger tool calls
    task = "List all Python files in the src directory using Glob, then read one of them."

    print(f"Task: {task}")
    print()

    if api_key:
        print("Running agent (this may take a moment)...")
        print("-" * 70)

        try:
            result = await agent.run_async(task)

            print()
            print("=" * 70)
            print("Agent Execution Complete")
            print("=" * 70)
            print()
            print(f"Final turn count: {result.get('turn_count', 'unknown')}")
            print(f"Tool results: {len(result.get('tool_results', []))}")
            print()
            print("Messages:")
            for i, msg in enumerate(result.get("messages", [])):
                msg_type = type(msg).__name__
                content = str(msg.content)[:100]
                print(f"  [{i}] {msg_type}: {content}...")
        except Exception as e:
            print(f"Error running agent: {e}")
            print()
            print("Make sure the TS Tool Server is running:")
            print("  cd ts_tool_server && npm run dev")
    else:
        # Mock demo without API key
        print("Mock demonstration (no API key):")
        print()
        print("The agent would follow this loop:")
        print()
        print("  1. reasoning: LLM analyzes task → decides to call tools")
        print("  2. tools: Glob tool searches for '**/*.py' files")
        print("  3. reasoning: LLM sees Glob results → decides to call Read")
        print("  4. tools: Read tool reads a Python file")
        print("  5. reasoning: LLM synthesizes findings → returns answer")
        print()
        print("  Graph structure:")
        print("    START → reasoning → [has_tool_calls?]")
        print("                       ├─ True  → tools → reasoning (loop)")
        print("                       └─ False → END")
        print()

    print()
    print("=" * 70)
    print("Demo complete!")
    print("=" * 70)


def demo_sync():
    """Synchronous demo wrapper."""
    asyncio.run(demo_agent_loop())


if __name__ == "__main__":
    demo_sync()
