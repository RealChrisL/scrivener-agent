"""
Daily follow-up notifier for ServiceFlow-Agent.
Run by cron at your preferred local time (see docs/setup.md for cron examples).
Sends a digest of stale open cases to all configured operators.
"""

import json
import sys
import os
import urllib.request

DATA_DIR = os.environ.get("SERVICEFLOW_DATA_DIR", os.path.expanduser("~/.claude/channels/line"))
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.abspath(_src))
sys.path.insert(0, DATA_DIR)

from airtable_crm import get_stale_records, record_url, _get_config
from config_loader import get_notify_user_ids

NOTIFY_USER_IDS = get_notify_user_ids()
STALE_DAYS = 1


def _get_line_token() -> str:
    env = {}
    env_path = os.path.join(DATA_DIR, ".env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env.get("LINE_CHANNEL_ACCESS_TOKEN", "")


def _send_line_message(user_id: str, text: str):
    token = _get_line_token()
    payload = json.dumps({
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }).encode()
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def main():
    records = get_stale_records(days=STALE_DAYS)
    if not records:
        print("No stale records.")
        return

    _, base_id, _ = _get_config()
    lines = [f"📋 Daily Follow-up | {len(records)} pending case(s)\n"]

    for r in records:
        f = r.get("fields", {})
        name     = f.get("name", "Unknown")
        case     = f.get("case_type", "Unknown")
        phone    = f.get("phone", "not provided")
        priority = f.get("priority", "")
        status   = f.get("status", "")
        url      = record_url(base_id, r["id"])
        icon = "🔴" if priority == "high_priority" else ("🟡" if priority == "normal" else "⚪")
        lines.append(f"{icon} {name} | {case}\n   📞 {phone} | {status}\n   🔗 {url}")

    message = "\n".join(lines)
    if len(message) > 4900:
        message = message[:4900] + "\n...(see Airtable for more)"

    for uid in NOTIFY_USER_IDS:
        _send_line_message(uid, message)
    print(f"Sent daily follow-up for {len(records)} records.")


if __name__ == "__main__":
    main()
