"""
Daily follow-up notifier — run by cron at 09:00 local time (adjust UTC offset for your timezone).
Sends a LINE summary of stale cases to the admin/operator.
"""

import json
import sys
import os
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from airtable_crm import get_stale_records, record_url, _get_config

NOTIFY_USER_IDS = [
    "YOUR_ADMIN_LINE_USER_ID",     # admin / operator
    "YOUR_DEVELOPER_LINE_USER_ID", # developer
]
STALE_DAYS = 1


def get_line_token():
    env = {}
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env.get("LINE_CHANNEL_ACCESS_TOKEN", "")


def send_line_message(user_id: str, text: str):
    token = get_line_token()
    url = "https://api.line.me/v2/bot/message/push"
    payload = json.dumps({
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }).encode()
    req = urllib.request.Request(
        url,
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
    lines = [f"📋 每日跟進提醒｜{len(records)} 筆待處理\n"]
    for r in records:
        f = r.get("fields", {})
        name = f.get("姓名", "未知")
        case = f.get("案件類型", "未知")
        phone = f.get("電話", "未提供")
        priority = f.get("優先級", "")
        status = f.get("進度狀態", "")
        url = record_url(base_id, r["id"])
        priority_icon = "🔴" if priority == "高優先" else ("🟡" if priority == "一般" else "⚪")
        lines.append(f"{priority_icon} {name}｜{case}\n   📞 {phone}｜{status}\n   🔗 {url}")

    message = "\n".join(lines)
    if len(message) > 4900:
        message = message[:4900] + "\n...（更多請查看 Airtable）"

    for uid in NOTIFY_USER_IDS:
        send_line_message(uid, message)
    print(f"Sent follow-up for {len(records)} records.")


if __name__ == "__main__":
    main()
