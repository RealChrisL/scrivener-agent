# LLM Adapter

ServiceFlow-Agent uses **Claude Code** (the `claude` CLI) as its LLM runtime.
The agent's entire behavior — persona, routing logic, CRM rules, escalation
heuristics — is defined in `CLAUDE.md` at the repository root. Changing how
the agent behaves means editing `CLAUDE.md`, not deploying code.

## Why Claude Code

- **Behavior = plain language.** Non-engineers can read and adjust the spec.
- **Native tool use.** Claude Code calls `Bash`, reads files, and uses MCP tools
  without additional scaffolding.
- **Persistent context.** The `--continue` flag resumes the session across restarts,
  maintaining conversation history.
- **Built-in safety.** Permission controls in `.claude/settings.local.json` restrict
  which tools Claude can call automatically.

## Model Selection

The Claude model is selected by the `claude` CLI. To target a specific model, pass
`--model` in `launch.sh`:

```bash
claude --model claude-opus-4-7 --dangerously-skip-permissions ...
```

Or set `CLAUDE_MODEL` in your environment if the CLI supports it.

## Extending to Other LLMs

While this framework is built around Claude Code, the architecture is compatible with
other LLM runtimes that support:

1. A persistent session loop (the agent keeps running between messages)
2. Tool use / function calling (for `Bash`, `Read`, and MCP tools)
3. An MCP client implementation (to receive channel notifications and call reply tools)

To swap the LLM:
1. Replace `launch.sh` with a launcher for your chosen runtime
2. Ensure the runtime reads `CLAUDE.md` (or an equivalent behavior spec) at startup
3. Map the tool names in `CLAUDE.md` (`mcp__line__reply`, `Bash`, etc.) to your
   runtime's equivalents
4. Update `.claude/settings.local.json` permissions for your runtime's permission model
