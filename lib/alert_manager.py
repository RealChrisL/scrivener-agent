"""
Persistent alert manager — resends high-priority notifications every 15 minutes
until the admin replies "已處理" or the case status changes to 人工接管中.
Max 3 resends (45 minutes total), then auto-clears.

Storage: ~/.claude/channels/line/pending_alerts.json
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

ALERTS_PATH = os.path.expanduser("~/.claude/channels/line/pending_alerts.json")
ENV_PATH = os.path.expanduser("~/.claude/channels/line/.env")
NOTIFY_USER_IDS = [
    "YOUR_ADMIN_LINE_USER_ID",     # admin / operator
    "YOUR_DEVELOPER_LINE_USER_ID", # developer
]
ADMIN_USER_ID = NOTIFY_USER_IDS[0]  # primary recipient for single-target calls
MAX_RESENDS = 3
RESEND_INTERVAL_MINUTES = 15


def _load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def _load_alerts():
    if not os.path.exists(ALERTS_PATH):
        return {}
    with open(ALERTS_PATH) as f:
        return json.load(f)


def _save_alerts(alerts):
    with open(ALERTS_PATH, "w") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)


def add_alert(user_id: str, message: str):
    """Register a new pending alert for a high-priority client."""
    alerts = _load_alerts()
    alerts[user_id] = {
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_sent_at": datetime.now(timezone.utc).isoformat(),
        "send_count": 1,
    }
    _save_alerts(alerts)


def clear_alert(user_id: str):
    """Clear a pending alert (called when the admin acknowledges or status changes)."""
    alerts = _load_alerts()
    if user_id in alerts:
        del alerts[user_id]
        _save_alerts(alerts)
        return True
    return False


def clear_all_alerts():
    """Clear all pending alerts."""
    _save_alerts({})


def _send_line_push(message: str):
    env = _load_env()
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    for uid in NOTIFY_USER_IDS:
        payload = json.dumps({
            "to": uid,
            "messages": [{"type": "text", "text": message}]
        }).encode()
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        urllib.request.urlopen(req)


def process_pending_alerts():
    """
    Check all pending alerts and resend if interval has passed.
    Called by cron every 15 minutes.
    """
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from airtable_crm import get_record

    alerts = _load_alerts()
    now = datetime.now(timezone.utc)
    updated = {}

    for user_id, alert in alerts.items():
        send_count = alert.get("send_count", 1)
        last_sent = datetime.fromisoformat(alert["last_sent_at"])
        minutes_elapsed = (now - last_sent).total_seconds() / 60

        # Check if Airtable status already changed to 人工接管中
        record = get_record(user_id)
        if record and record.get("fields", {}).get("進度狀態") == "人工接管中":
            print(f"Alert cleared for {user_id} — status changed to 人工接管中")
            continue  # Don't carry over this alert

        # Max resends reached
        if send_count >= MAX_RESENDS:
            print(f"Alert max resends reached for {user_id} — auto-clearing")
            continue

        # Not yet time to resend
        if minutes_elapsed < RESEND_INTERVAL_MINUTES:
            updated[user_id] = alert
            continue

        # Resend
        resend_msg = (
            f"🔴🔴🔴 重發通知（第{send_count + 1}次）請立即處理\n"
            + alert["message"].split("\n", 1)[1]  # Keep original content, update header
            + f"\n\n（回覆「已處理」停止通知）"
        )
        try:
            _send_line_push(resend_msg)
            alert["last_sent_at"] = now.isoformat()
            alert["send_count"] = send_count + 1
            updated[user_id] = alert
            print(f"Resent alert for {user_id} (count: {send_count + 1})")
        except Exception as e:
            print(f"Failed to resend alert for {user_id}: {e}")
            updated[user_id] = alert

    _save_alerts(updated)
    return len(updated)


def handle_acknowledgment(admin_message: str) -> bool:
    """
    Returns True if the message is an acknowledgment keyword.
    Called when the admin sends a message to the bot.
    """
    keywords = {"已處理", "已看到", "ok", "OK", "好", "收到"}
    return admin_message.strip() in keywords


if __name__ == "__main__":
    pending = process_pending_alerts()
    print(f"Processed {pending} pending alerts")
