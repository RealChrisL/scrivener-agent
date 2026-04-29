"""
Airtable CRM module for a LINE bot agent.
Reads credentials from ~/.claude/channels/line/.env
Required env vars: AIRTABLE_API_TOKEN, AIRTABLE_BASE_ID
TABLE_NAME defaults to '客戶紀錄'
"""

import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

ENV_PATH = os.path.expanduser("~/.claude/channels/line/.env")
CACHE_PATH = os.path.expanduser("~/.claude/channels/line/crm_cache.json")
CACHE_TTL_SECONDS = 300  # 5 minutes


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: dict):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, ensure_ascii=False)


def _cache_get(user_id: str) -> dict | None:
    cache = _load_cache()
    entry = cache.get(user_id)
    if not entry:
        return None
    if time.time() - entry.get("ts", 0) > CACHE_TTL_SECONDS:
        return None  # expired
    return entry.get("record")


def _cache_set(user_id: str, record: dict | None):
    cache = _load_cache()
    if record is None:
        cache.pop(user_id, None)
    else:
        cache[user_id] = {"record": record, "ts": time.time()}
    _save_cache(cache)


def _cache_invalidate(user_id: str):
    cache = _load_cache()
    cache.pop(user_id, None)
    _save_cache(cache)


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


def _get_config():
    env = _load_env()
    token = env.get("AIRTABLE_API_TOKEN", "")
    base_id = env.get("AIRTABLE_BASE_ID", "")
    table = env.get("TABLE_NAME", "客戶紀錄")
    if not token or not base_id:
        raise RuntimeError("AIRTABLE_API_TOKEN and AIRTABLE_BASE_ID must be set in .env")
    return token, base_id, table


def _api(method, path, data=None):
    token, base_id, table = _get_config()
    encoded_table = urllib.parse.quote(table, safe="")
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Airtable API error {e.code}: {e.read().decode()}") from e


def get_record(user_id: str, bypass_cache: bool = False) -> dict | None:
    """Return existing Airtable record for userId, or None. Uses local cache."""
    if not bypass_cache:
        cached = _cache_get(user_id)
        if cached is not None:
            return cached
    formula = urllib.parse.quote(f"{{LINE用戶ID}}='{user_id}'")
    result = _api("GET", f"?filterByFormula={formula}&maxRecords=1")
    records = result.get("records", [])
    record = records[0] if records else None
    _cache_set(user_id, record)
    return record


def create_record(data: dict) -> dict:
    """Create a new CRM record. data keys = Airtable field names."""
    payload = {"records": [{"fields": data}]}
    result = _api("POST", "", payload)
    record = result["records"][0]
    uid = data.get("LINE用戶ID")
    if uid:
        _cache_set(uid, record)
    return record


def update_record(record_id: str, data: dict, user_id: str | None = None) -> dict:
    """Update an existing record. Invalidates cache for user_id if provided."""
    payload = {"records": [{"id": record_id, "fields": data}]}
    result = _api("PATCH", "", payload)
    record = result["records"][0]
    # Invalidate cache by LINE用戶ID if known
    uid = user_id or record.get("fields", {}).get("LINE用戶ID")
    if uid:
        _cache_invalidate(uid)
    return record


def upsert_customer(user_id: str, analysis: dict) -> tuple[dict, bool]:
    """
    Create or update a customer record from an analysis dict.
    Returns (record, created) where created=True if new record.

    Expected analysis keys (all optional):
        姓名, 性別, 電話, 案件類型, 需求摘要, 客戶Persona,
        優先級, 優先級判斷原因, Follow-up Action Items (list),
        對話摘要
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    action_items = analysis.get("Follow-up Action Items", [])
    if isinstance(action_items, list):
        action_items_str = "\n".join(f"・{i}" for i in action_items)
    else:
        action_items_str = str(action_items)

    fields = {
        "LINE用戶ID": user_id,
        "最後互動時間": now,
    }

    field_map = {
        "姓名": "姓名",
        "性別": "性別",
        "電話": "電話",
        "案件類型": "案件類型",
        "需求摘要": "需求摘要",
        "客戶類型": "客戶類型",
        "優先級": "優先級",
        "優先級判斷原因": "優先級判斷原因",
        "對話摘要": "對話摘要",
        "客戶場景描述": "客戶場景描述",
        "問卷回答摘要": "問卷回答摘要",
    }
    for src, dst in field_map.items():
        val = analysis.get(src, "")
        if val:
            fields[dst] = val

    if action_items_str:
        fields["待辦事項"] = action_items_str

    existing = get_record(user_id)
    if existing:
        current_status = existing.get("fields", {}).get("進度狀態", "")
        # Terminal state: never touch the record
        if current_status == "已完成":
            return existing, False
        # During handover: update CRM but preserve the status
        if current_status == "人工接管中":
            fields.pop("進度狀態", None)
        record = update_record(existing["id"], fields)
        return record, False
    else:
        fields["首次進線時間"] = now
        fields["進度狀態"] = "跟進中"
        record = create_record(fields)
        return record, True


def get_bot_mode(user_id: str) -> str:
    """
    Return bot mode for this user based on Airtable status.

    Simplified 4-state model:
      進行中      → 'reply'   Bot replies + updates CRM
      暫停        → 'reply'   Bot replies + updates CRM (no questionnaire push)
      人工接管中   → 'silent'  Bot does NOT reply, but updates CRM in background
      已完成      → 'off'     Bot does nothing (terminal)

    Legacy statuses (新進線/跟進中/已委託) map to 'reply' for backward compat.
    """
    existing = get_record(user_id)
    if not existing:
        return "reply"
    status = existing.get("fields", {}).get("進度狀態", "")
    if status == "已完成":
        return "off"
    if status == "人工接管中":
        return "silent"
    return "reply"  # 進行中, 暫停, legacy statuses


def is_handover(user_id: str) -> bool:
    """Return True if this user is currently in human handover mode (bot silent)."""
    return get_bot_mode(user_id) == "silent"


def get_stale_records(days: int = 3) -> list[dict]:
    """Return records not updated in the last `days` days, excluding 已完成."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    formula = urllib.parse.quote(
        f"AND(IS_BEFORE({{最後互動時間}}, '{cutoff}'), {{進度狀態}} != '已完成')"
    )
    result = _api("GET", f"?filterByFormula={formula}&maxRecords=50")
    return result.get("records", [])


TABLE_ID = "YOUR_TABLE_ID"  # 客戶紀錄 — find this in your Airtable URL: airtable.com/YOUR_BASE_ID/YOUR_TABLE_ID

def record_url(base_id: str, record_id: str) -> str:
    return f"https://airtable.com/{base_id}/{TABLE_ID}/{record_id}"


def find_record_by_name(name: str) -> dict | None:
    """Find a record by 姓名 field (partial match)."""
    formula = urllib.parse.quote(f"FIND('{name}', {{姓名}}) > 0")
    result = _api("GET", f"?filterByFormula={formula}&maxRecords=1")
    records = result.get("records", [])
    return records[0] if records else None


def set_status(user_id: str | None = None, name: str | None = None, status: str = "") -> dict | None:
    """Set 進度狀態 by userId or name. Returns updated record or None."""
    record = get_record(user_id) if user_id else None
    if not record and name:
        record = find_record_by_name(name)
    if not record:
        return None
    uid = user_id or record.get("fields", {}).get("LINE用戶ID")
    return update_record(record["id"], {"進度狀態": status}, user_id=uid)


def _get_last_alert_name() -> str | None:
    """Return the 姓名 of the most recent pending alert, or None."""
    import json as _json
    alerts_path = os.path.expanduser("~/.claude/channels/line/pending_alerts.json")
    if not os.path.exists(alerts_path):
        return None
    try:
        with open(alerts_path) as f:
            alerts = _json.load(f)
        if not alerts:
            return None
        # Most recent by created_at
        latest_uid = max(alerts, key=lambda u: alerts[u].get("created_at", ""))
        record = get_record(latest_uid)
        if record:
            return record["fields"].get("姓名")
    except Exception:
        pass
    return None


def handle_admin_command(text: str) -> dict | None:
    """
    Parse and execute admin commands from the admin/operator.
    Returns dict with keys: command, name, record, url, message
    Returns None if not a recognized command.

    Supported commands:
      查 {姓名}      — lookup record
      接管 [{姓名}]  — set 人工接管中 (no name = last high-priority alert)
      恢復 [{姓名}]  — set 跟進中
      結案 [{姓名}]  — set 已完成
    """
    text = text.strip()
    for cmd, status, label in [
        ("接管", "人工接管中", "Bot 已靜默，您可直接接手"),
        ("恢復", "跟進中",    "Bot 已恢復自動回覆"),
        ("結案", "已完成",    "案件已結案，Bot 退出"),
        ("查",   None,        ""),
    ]:
        if text.startswith(cmd + " ") or text.startswith(cmd) or text == cmd:
            name = text[len(cmd):].strip()
            if not name:
                if cmd == "查":
                    return {"command": cmd, "message": f"請輸入姓名，例如：查 陳雅婷"}
                # No name: fall back to last high-priority alert
                name = _get_last_alert_name()
                if not name:
                    return {"command": cmd, "message": f"找不到最近的高優先案件，請輸入姓名：{cmd} 陳雅婷"}

            if status:
                record = set_status(name=name, status=status)
                if not record:
                    return {"command": cmd, "message": f"找不到客戶「{name}」，請確認姓名"}
                _, base_id, _ = _get_config()
                url = record_url(base_id, record["id"])
                return {"command": cmd, "name": name, "record": record, "url": url,
                        "message": f"✅ {name}｜{label}\n🔗 {url}"}
            else:
                # 查
                record = find_record_by_name(name)
                if not record:
                    return {"command": cmd, "message": f"找不到客戶「{name}」"}
                f = record["fields"]
                _, base_id, _ = _get_config()
                url = record_url(base_id, record["id"])
                return {
                    "command": cmd, "name": name, "record": record, "url": url,
                    "message": (
                        f"📋 {f.get('姓名','?')}\n"
                        f"📞 {f.get('電話','未提供')}\n"
                        f"案件：{f.get('案件類型','?')} | 狀態：{f.get('進度狀態','?')}\n"
                        f"優先級：{f.get('優先級','?')}\n"
                        f"LINE用戶ID：{f.get('LINE用戶ID','?')}\n"
                        f"🔗 {url}"
                    )
                }
    return None
