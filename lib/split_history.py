"""
Splits the shared history.log into per-user log files.
Run by cron every minute. Uses a position file to avoid reprocessing.
"""
import os
import re
from pathlib import Path

HISTORY_LOG = os.path.expanduser("~/.claude/channels/line/history.log")
USER_LOG_DIR = os.path.expanduser("~/.claude/channels/line/history/")
POSITION_FILE = os.path.join(USER_LOG_DIR, ".position")

Path(USER_LOG_DIR).mkdir(exist_ok=True)

position = 0
if os.path.exists(POSITION_FILE):
    try:
        with open(POSITION_FILE) as f:
            position = int(f.read().strip() or 0)
    except ValueError:
        position = 0

with open(HISTORY_LOG, "rb") as f:
    f.seek(position)
    new_bytes = f.read()
    new_position = f.tell()

if not new_bytes:
    exit(0)

new_content = new_bytes.decode("utf-8", errors="replace")
count = 0
for line in new_content.splitlines():
    match = re.search(r"\[user:([^\]]+)\]", line)
    if match:
        user_id = match.group(1)
        user_log = os.path.join(USER_LOG_DIR, f"{user_id}.log")
        with open(user_log, "a") as f:
            f.write(line + "\n")
        count += 1

with open(POSITION_FILE, "w") as f:
    f.write(str(new_position))

if count:
    print(f"Split {count} lines into per-user logs")
