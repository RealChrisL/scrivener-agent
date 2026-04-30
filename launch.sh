#!/bin/bash
# AGENT_DIR: the directory where your deployed CLAUDE.md lives.
# Defaults to the directory this script resides in.
AGENT_DIR="${AGENT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
PROJ=~/.claude/projects/$(realpath "$AGENT_DIR" | sed 's|/|-|g' | sed 's|^-||')
MAX_SIZE=3000000

JSONL=$(ls "$PROJ"/*.jsonl 2>/dev/null | head -1)
if [ -n "$JSONL" ] && [ "$(wc -c < "$JSONL")" -gt "$MAX_SIZE" ]; then
  LINES=$(wc -l < "$JSONL")
  KEEP=$(( LINES * 2000000 / $(wc -c < "$JSONL") ))
  tail -n "$KEEP" "$JSONL" > "$JSONL.tmp" && mv "$JSONL.tmp" "$JSONL"
fi

CONTINUE=""
ls "$PROJ"/*.jsonl 2>/dev/null | grep -q . && CONTINUE="--continue"

while true; do
  claude --dangerously-skip-permissions $CONTINUE \
    --dangerously-load-development-channels server:line
  CONTINUE="--continue"
  echo "Claude exited, restarting in 5 seconds..."
  sleep 5
done
