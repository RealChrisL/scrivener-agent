"""
Persistent alert manager for ServiceFlow-Agent.

Resends high-priority notifications every RESEND_INTERVAL_MINUTES until the
operator replies with an acknowledgment keyword or the case status changes to
human_takeover. Maximum MAX_RESENDS attempts before auto-clearing.

Storage: {SERVICEFLOW_DATA_DIR}/pending_alerts.json
Run by cron every 15 minutes.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

DATA_DIR = os.environ.get("SERVICEFLOW_DATA_DIR", os.path.expanduser("~/.claude/channels/line"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Allow running from repo root or deployed location
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.abspath(_src))
sys.path.insert(0, DATA_DIR)

from config_loader import get_notify_user_ids

ALERTS_PATH = os.path.join(DATA_DIR, "pending_alerts.json")
ENV_PATH = os.path.join(DATA_DIR, ".env")
NOTIFY_USER_IDS = get_notify_user_ids()
MAX_RESENDS = 3
RESEND_INTERVAL_MINUTES = 15

# Operator replies any of these to stop alert resends
ACK_KEYWORDS = {"acknowledged", "ack", "ok", "noted", "seen"}


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


def _load_alerts() -> dict:
    if not os.path.exists(ALERTS_PATH):
        return {}
    with open(ALERTS_PATH) as f:
        return json.load(f)


def _save_alerts(alerts: dict):
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


def clear_alert(user_id: str) -> bool:
    """Clear the pending alert for a specific user."""
    alerts = _load_alerts()
    if user_id in alerts:
        del alerts[user_id]
        _save_alerts(alerts)
        return True
    return False


def clear_all_alerts():
    """Clear all pending alerts."""
    _save_alerts({})


def _send_push(message: str):
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
    Check all pending alerts and resend those past the interval threshold.
    Clears alerts automatically when case status is already human_takeover.
    Called by cron every 15 minutes.
    """
    from airtable_crm import get_record

    alerts = _load_alerts()
    now = datetime.now(timezone.utc)
    updated = {}

    for user_id, alert in alerts.items():
        send_count = alert.get("send_count", 1)
        last_sent = datetime.fromisoformat(alert["last_sent_at"])
        minutes_elapsed = (now - last_sent).total_seconds() / 60

        # Auto-clear if operator already took over in CRM
        record = get_record(user_id)
        if record and record.get("fields", {}).get("status") == "human_takeover":
            print(f"Alert cleared for {user_id} — status is human_takeover")
            continue

        if send_count >= MAX_RESENDS:
            print(f"Alert max resends reached for {user_id} — auto-clearing")
            continue

        if minutes_elapsed < RESEND_INTERVAL_MINUTES:
            updated[user_id] = alert
            continue

        parts = alert["message"].split("\n", 1)
        body = parts[1] if len(parts) > 1 else parts[0]
        resend_msg = (
            f"🔴🔴🔴 Alert Resend #{send_count + 1} — Action Required\n"
            + body
            + "\n\n(Reply 'acknowledged' to stop notifications)"
        )
        try:
            _send_push(resend_msg)
            alert["last_sent_at"] = now.isoformat()
            alert["send_count"] = send_count + 1
            updated[user_id] = alert
            print(f"Resent alert for {user_id} (count: {send_count + 1})")
        except Exception as e:
            print(f"Failed to resend alert for {user_id}: {e}")
            updated[user_id] = alert

    _save_alerts(updated)
    return len(updated)


def handle_acknowledgment(operator_message: str) -> bool:
    """Return True if the operator's message is an acknowledgment keyword."""
    return operator_message.strip().lower() in ACK_KEYWORDS


if __name__ == "__main__":
    pending = process_pending_alerts()
    print(f"Processed {pending} pending alerts")
