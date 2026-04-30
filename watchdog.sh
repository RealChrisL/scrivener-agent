#!/bin/bash
# 在另一個 tmux session 執行：tmux new-session -d -s watchdog "bash watchdog.sh"
GRACE=0
NGROK_SESSION="ngrok"
NGROK_PORT=3456

start_ngrok() {
  tmux has-session -t "$NGROK_SESSION" 2>/dev/null && tmux kill-session -t "$NGROK_SESSION"
  tmux new-session -d -s "$NGROK_SESSION" "ngrok http $NGROK_PORT"
  echo "$(date): Started ngrok http $NGROK_PORT in tmux session '$NGROK_SESSION'."
}

is_ngrok_up() {
  tmux has-session -t "$NGROK_SESSION" 2>/dev/null || return 1
  curl -sf http://localhost:4040/api/tunnels > /dev/null 2>&1
}

# Start ngrok on watchdog launch
start_ngrok

while true; do
  PANE_PID=$(tmux list-panes -t line-agent -F '#{pane_pid}' 2>/dev/null | head -1)
  # 自動確認 development channels 對話框
  tmux send-keys -t line-agent "" Enter 2>/dev/null

  if [ "$GRACE" -le 0 ] && ! ss -tlnp | grep -q ":$NGROK_PORT "; then
    CLAUDE_PID=$(pstree -p "$PANE_PID" 2>/dev/null | grep -o 'claude([0-9]*)' | head -1 | grep -o '[0-9]*')
    if [ -n "$CLAUDE_PID" ]; then
      echo "$(date): bun MCP server 停止回應，重啟 Claude ($CLAUDE_PID)"
      kill "$CLAUDE_PID"
      GRACE=6  # 60 秒 grace period
    fi
  fi

  # Recover ngrok if down
  if ! is_ngrok_up; then
    echo "$(date): ngrok is down. Restarting..."
    start_ngrok
  fi

  [ "$GRACE" -gt 0 ] && GRACE=$((GRACE - 1))
  sleep 10
done
