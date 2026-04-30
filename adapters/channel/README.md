# Channel Adapters

A **channel adapter** connects an external messaging platform to the ServiceFlow-Agent
orchestration layer. It receives incoming messages (typically via webhook), delivers them
to Claude Code as MCP notifications, and sends replies back through the platform's API.

## Current Implementations

| Channel | Status | Directory |
|---------|--------|-----------|
| LINE Messaging API | ✅ Production-ready | `line/` |
| WhatsApp Business API | 🗺️ Planned | — |
| Telegram Bot API | 🗺️ Planned | — |
| Web Chat (WebSocket) | 🗺️ Planned | — |

## LINE Adapter

The LINE adapter uses the [`claude-line-channel`](https://github.com/anthropics/claude-line-channel)
MCP plugin, which runs a bun-based webhook server on port 3456 and delivers LINE events
to Claude Code via the MCP protocol.

**Files:**
- `line/start.sh` — starts the bun MCP server
- `line/launch.sh` — starts the Claude Code session (auto-restart + context trimming)
- `line/watchdog.sh` — process guardian keeping bun + ngrok alive
- `line/.mcp.json` — MCP plugin wiring

**Setup:** See [docs/setup.md](../../docs/setup.md) for full LINE adapter setup instructions.

## Building a New Channel Adapter

To add support for a new messaging platform:

### 1. Create the MCP plugin (or use an existing one)

The adapter needs to:
- Receive webhooks from the platform
- Forward them to Claude Code as MCP tool-call notifications
- Expose a `reply` tool that Claude can call to send messages back

### 2. Create the adapter directory

```
adapters/channel/<platform>/
├── start.sh       # starts the webhook server / MCP bridge
├── launch.sh      # starts Claude Code with the adapter loaded
└── .mcp.json      # MCP server wiring
```

### 3. Update CLAUDE.md

In `CLAUDE.md`, the **Behavior** section tells Claude which MCP tool to use for replies
and how to read inbound message metadata. Update the tool names to match your adapter
(e.g. `mcp__whatsapp__reply` instead of `mcp__line__reply`).

### 4. Environment variables

Channel adapters read credentials from `$SERVICEFLOW_DATA_DIR/.env`. Add your platform's
credentials there and document them in `.env.example`.

### 5. Data directory

Inbound media files should be saved under `$SERVICEFLOW_DATA_DIR/inbox/`.
History logs should append to `$SERVICEFLOW_DATA_DIR/history.log` in the format:
```
[timestamp] [user:<user_id>] <message_text>
```
so that `src/history/split_history.py` can fan them out to per-user logs.
