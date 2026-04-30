#!/bin/bash
# Process guardian for ServiceFlow-Agent (LINE channel).
# Keeps the bun MCP server and ngrok tunnel alive.
# Run in a separate tmux session:
#   tmux new-session -d -s watchdog "bash adapters/channel/line/watchdog.sh"
#
# Environment variables:
#   LINE_WEBHOOK_PORT — port the bun MCP server listens on (default: 3456)
#   AGENT_SESSION     — tmux session name for the Claude agent (default: line-agent)

GRACE=0
NGROK_SESSION="ngrok"
LINE_WEBHOOK_PORT="${LINE_WEBHOOK_PORT:-3456}"
AGENT_SESSION="${AGENT_SESSION:-line-agent}"

start_ngrok() {
  tmux has-session -t "$NGROK_SESSION" 2>/dev/null && tmux kill-session -t "$NGROK_SESSION"
  tmux new-session -d -s "$NGROK_SESSION" "ngrok http $LINE_WEBHOOK_PORT"
  echo "$(date): Started ngrok http $LINE_WEBHOOK_PORT in tmux session '$NGROK_SESSION'."
}

is_ngrok_up() {
  tmux has-session -t "$NGROK_SESSION" 2>/dev/null || return 1
  curl -sf http://localhost:4040/api/tunnels > /dev/null 2>&1
}

start_ngrok

while true; do
  PANE_PID=$(tmux list-panes -t "$AGENT_SESSION" -F '#{pane_pid}' 2>/dev/null | head -1)
  # Auto-confirm any development channels dialog
  tmux send-keys -t "$AGENT_SESSION" "" Enter 2>/dev/null

  if [ "$GRACE" -le 0 ] && ! ss -tlnp | grep -q ":$LINE_WEBHOOK_PORT "; then
    CLAUDE_PID=$(pstree -p "$PANE_PID" 2>/dev/null | grep -o 'claude([0-9]*)' | head -1 | grep -o '[0-9]*')
    if [ -n "$CLAUDE_PID" ]; then
      echo "$(date): bun MCP server unresponsive — restarting Claude (PID $CLAUDE_PID)"
      kill "$CLAUDE_PID"
      GRACE=6  # 60-second grace period (6 × 10s sleep)
    fi
  fi

  if ! is_ngrok_up; then
    echo "$(date): ngrok is down — restarting..."
    start_ngrok
  fi

  [ "$GRACE" -gt 0 ] && GRACE=$((GRACE - 1))
  sleep 10
done
