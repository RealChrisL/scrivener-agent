#!/bin/bash
# Starts the LINE webhook MCP server (bun runtime).
# Requires the claude-line-channel plugin to be installed:
#   claude mcp add claude-line-channel
#
# Environment variables:
#   PLUGIN_DIR   — override auto-detected plugin path
#   LINE_WEBHOOK_PORT — override default port 3456 (default)

export PATH="$HOME/.bun/bin:$PATH"
fuser -k "${LINE_WEBHOOK_PORT:-3456}/tcp" 2>/dev/null || true

# Auto-detect installed plugin directory.
# If detection fails, set PLUGIN_DIR manually:
#   export PLUGIN_DIR=~/.claude/plugins/cache/claude-line-channel/line/<hash>
PLUGIN_DIR="${PLUGIN_DIR:-$(ls -d ~/.claude/plugins/cache/claude-line-channel/line/*/ 2>/dev/null | head -1)}"
if [ -z "$PLUGIN_DIR" ]; then
  echo "Error: claude-line-channel plugin not found. Run: claude mcp add claude-line-channel"
  exit 1
fi

LINE_WEBHOOK_PORT="${LINE_WEBHOOK_PORT:-3456}" \
exec "$HOME/.bun/bin/bun" run --cwd "$PLUGIN_DIR" start
