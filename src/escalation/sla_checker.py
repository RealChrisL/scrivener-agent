"""
SLA breach checker for ServiceFlow-Agent.
Run by cron every 30 minutes.

Notifies configured operators if a client has not been responded to within
SLA_HOURS. A record is "responded" when its status is human_takeover or
completed. Breach = record created > SLA_HOURS ago AND still active/paused.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

DATA_DIR = os.environ.get("SERVICEFLOW_DATA_DIR", os.path.expanduser("~/.claude/channels/line"))
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.abspath(_src))
sys.path.insert(0, DATA_DIR)

from airtable_crm import _get_config, record_url
from config_loader import get_notify_user_ids

SLA_HOURS = 4
NOTIFY_USER_IDS = get_notify_user_ids()
ENV_PATH = os.path.join(DATA_DIR, ".env")
SLA_LOG = os.path.join(DATA_DIR, "sla.log")


def _load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _push(token: str, message: str):
    for uid in NOTIFY_USER_IDS:
        payload = json.dumps({"to": uid, "messages": [{"type": "text", "text": message}]}).encode()
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        urllib.request.urlopen(req)


def main():
    api_key, base_id, table_name = _get_config()
    import urllib.parse
    encoded_table = urllib.parse.quote(table_name)

    filter_formula = urllib.parse.quote("OR({status}='active',{status}='paused')")
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}?filterByFormula={filter_formula}&maxRecords=100"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    res = urllib.request.urlopen(req)
    records = json.loads(res.read()).get("records", [])

    now = datetime.now(timezone.utc)
    breaches = []

    for r in records:
        created_str = r.get("createdTime", "")
        if not created_str:
            continue
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        age_hours = (now - created).total_seconds() / 3600

        if age_hours >= SLA_HOURS:
            f = r.get("fields", {})
            breaches.append({
                "name":      f.get("name", "Unknown"),
                "case_type": f.get("case_type", "Unknown"),
                "phone":     f.get("phone", "not provided"),
                "status":    f.get("status", ""),
                "age_hours": round(age_hours, 1),
                "url":       record_url(base_id, r["id"]),
            })

    if not breaches:
        print("No SLA breaches.")
        return

    env = _load_env()
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")

    lines = [f"🟡 SLA Breach Alert | {len(breaches)} case(s) unresponded for over {SLA_HOURS} hours\n"]
    for b in breaches:
        lines.append(
            f"👤 {b['name']} | {b['case_type']}\n"
            f"   📞 {b['phone']} | {b['status']}\n"
            f"   ⏱ Waiting {b['age_hours']} hours\n"
            f"   🔗 {b['url']}"
        )

    message = "\n".join(lines)
    if len(message) > 4900:
        message = message[:4900] + "\n...(see Airtable for more)"

    _push(token, message)
    print(f"Sent SLA breach notification for {len(breaches)} records.")

    with open(SLA_LOG, "a") as f:
        f.write(f"{now.isoformat()} — {len(breaches)} breaches notified\n")


if __name__ == "__main__":
    main()
