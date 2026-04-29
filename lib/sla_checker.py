"""
SLA breach checker.
Run by cron every 30 minutes.
Notifies the admin and developer if a client has not been responded to within SLA_HOURS.

A record is considered "responded" if its 進度狀態 is 人工接管中 or 已完成.
SLA breach = record created > SLA_HOURS ago AND still 跟進中 or 暫停.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from airtable_crm import _get_config, record_url

SLA_HOURS = 4
NOTIFY_USER_IDS = [
    "YOUR_ADMIN_LINE_USER_ID",     # admin / operator
    "YOUR_DEVELOPER_LINE_USER_ID", # developer
]
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
SLA_LOG = os.path.join(os.path.dirname(__file__), "sla.log")


def _load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _push(token, message):
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

    # Fetch all open records (跟進中 or 暫停)
    filter_formula = urllib.parse.quote("OR({進度狀態}='跟進中',{進度狀態}='暫停')")
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
                "name": f.get("姓名", "未知"),
                "case": f.get("案件類型", "未知"),
                "phone": f.get("電話", "未提供"),
                "status": f.get("進度狀態", ""),
                "age_hours": round(age_hours, 1),
                "url": record_url(base_id, r["id"]),
            })

    if not breaches:
        print("No SLA breaches.")
        return

    env = _load_env()
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")

    lines = [f"🟡 SLA 逾時提醒｜{len(breaches)} 筆未回覆超過 {SLA_HOURS} 小時\n"]
    for b in breaches:
        lines.append(
            f"👤 {b['name']}｜{b['case']}\n"
            f"   📞 {b['phone']}｜{b['status']}\n"
            f"   ⏱ 已等待 {b['age_hours']} 小時\n"
            f"   🔗 {b['url']}"
        )

    message = "\n".join(lines)
    if len(message) > 4900:
        message = message[:4900] + "\n...（更多請查看 Airtable）"

    _push(token, message)
    print(f"Sent SLA breach notification for {len(breaches)} records.")

    with open(SLA_LOG, "a") as f:
        f.write(f"{now.isoformat()} — {len(breaches)} breaches notified\n")


if __name__ == "__main__":
    main()
