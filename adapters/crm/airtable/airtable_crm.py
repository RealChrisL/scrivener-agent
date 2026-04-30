"""
Airtable CRM adapter for ServiceFlow-Agent.

Reads credentials from the runtime data directory (SERVICEFLOW_DATA_DIR,
default: ~/.claude/channels/line). Required env vars in .env:
  AIRTABLE_API_TOKEN, AIRTABLE_BASE_ID
  TABLE_NAME  (optional — defaults to 'client_records')

Field names match the schema in config/crm_schema.example.json.
"""

import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

DATA_DIR = os.environ.get("SERVICEFLOW_DATA_DIR", os.path.expanduser("~/.claude/channels/line"))
ENV_PATH = os.path.join(DATA_DIR, ".env")
CACHE_PATH = os.path.join(DATA_DIR, "crm_cache.json")
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
        return None
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
    table = env.get("TABLE_NAME", "client_records")
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
    """Return existing Airtable record for this channel user ID, or None."""
    if not bypass_cache:
        cached = _cache_get(user_id)
        if cached is not None:
            return cached
    formula = urllib.parse.quote(f"{{channel_user_id}}='{user_id}'")
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
    uid = data.get("channel_user_id")
    if uid:
        _cache_set(uid, record)
    return record


def update_record(record_id: str, data: dict, user_id: str | None = None) -> dict:
    """Update an existing record and invalidate its cache entry."""
    payload = {"records": [{"id": record_id, "fields": data}]}
    result = _api("PATCH", "", payload)
    record = result["records"][0]
    uid = user_id or record.get("fields", {}).get("channel_user_id")
    if uid:
        _cache_invalidate(uid)
    return record


def upsert_customer(user_id: str, analysis: dict) -> tuple[dict, bool]:
    """
    Create or update a customer record from a conversation analysis dict.
    Returns (record, created) where created=True if this is a new record.

    Expected analysis keys (all optional):
        name, gender, phone, case_type, summary, client_type,
        priority, priority_reason, action_items (list), conversation_summary,
        client_scenario, questionnaire_summary
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    action_items = analysis.get("action_items", [])
    if isinstance(action_items, list):
        action_items_str = "\n".join(f"• {i}" for i in action_items)
    else:
        action_items_str = str(action_items)

    fields = {
        "channel_user_id": user_id,
        "last_interaction_at": now,
    }

    field_map = {
        "name":                   "name",
        "gender":                 "gender",
        "phone":                  "phone",
        "case_type":              "case_type",
        "summary":                "summary",
        "client_type":            "client_type",
        "priority":               "priority",
        "priority_reason":        "priority_reason",
        "conversation_summary":   "conversation_summary",
        "client_scenario":        "client_scenario",
        "questionnaire_summary":  "questionnaire_summary",
    }
    for src, dst in field_map.items():
        val = analysis.get(src, "")
        if val:
            fields[dst] = val

    if action_items_str:
        fields["action_items"] = action_items_str

    existing = get_record(user_id)
    if existing:
        current_status = existing.get("fields", {}).get("status", "")
        if current_status == "completed":
            return existing, False
        if current_status == "human_takeover":
            fields.pop("status", None)
        record = update_record(existing["id"], fields)
        return record, False
    else:
        fields["first_contact_at"] = now
        fields["status"] = "active"
        record = create_record(fields)
        return record, True


def get_agent_mode(user_id: str) -> str:
    """
    Return the agent's operating mode for this user based on CRM status.

    4-state model:
      active / in_progress / paused  → 'reply'   Agent replies + updates CRM
      human_takeover                 → 'silent'  Agent records CRM only, no reply
      completed                      → 'off'     Agent does nothing (terminal state)
      no record                      → 'reply'   Default for new users
    """
    existing = get_record(user_id)
    if not existing:
        return "reply"
    status = existing.get("fields", {}).get("status", "")
    if status == "completed":
        return "off"
    if status == "human_takeover":
        return "silent"
    return "reply"


def is_handover(user_id: str) -> bool:
    """Return True if this user is currently in human handover mode (agent silent)."""
    return get_agent_mode(user_id) == "silent"


def get_stale_records(days: int = 3) -> list[dict]:
    """Return records not updated in the last `days` days, excluding completed."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    formula = urllib.parse.quote(
        f"AND(IS_BEFORE({{last_interaction_at}}, '{cutoff}'), {{status}} != 'completed')"
    )
    result = _api("GET", f"?filterByFormula={formula}&maxRecords=50")
    return result.get("records", [])


TABLE_ID = "YOUR_TABLE_ID"  # Find this in your Airtable URL: airtable.com/BASE_ID/TABLE_ID

def record_url(base_id: str, record_id: str) -> str:
    return f"https://airtable.com/{base_id}/{TABLE_ID}/{record_id}"


def find_record_by_name(name: str) -> dict | None:
    """Find a record by name field (partial match)."""
    formula = urllib.parse.quote(f"FIND('{name}', {{name}}) > 0")
    result = _api("GET", f"?filterByFormula={formula}&maxRecords=1")
    records = result.get("records", [])
    return records[0] if records else None


def set_status(user_id: str | None = None, name: str | None = None, status: str = "") -> dict | None:
    """Set status field by channel user ID or name. Returns updated record or None."""
    record = get_record(user_id) if user_id else None
    if not record and name:
        record = find_record_by_name(name)
    if not record:
        return None
    uid = user_id or record.get("fields", {}).get("channel_user_id")
    return update_record(record["id"], {"status": status}, user_id=uid)


def _get_last_alert_name() -> str | None:
    """Return the name from the most recent pending alert, or None."""
    alerts_path = os.path.join(DATA_DIR, "pending_alerts.json")
    if not os.path.exists(alerts_path):
        return None
    try:
        with open(alerts_path) as f:
            alerts = json.load(f)
        if not alerts:
            return None
        latest_uid = max(alerts, key=lambda u: alerts[u].get("created_at", ""))
        record = get_record(latest_uid)
        if record:
            return record["fields"].get("name")
    except Exception:
        pass
    return None


def handle_admin_command(text: str) -> dict | None:
    """
    Parse and execute operator commands.
    Returns dict with keys: command, name, record, url, message
    Returns None if not a recognized command.

    Supported commands:
      lookup {name}    — look up a client record
      takeover {name}  — set status to human_takeover (agent goes silent)
      resume {name}    — set status to active (agent resumes)
      close {name}     — set status to completed (case closed)
    """
    text = text.strip()
    for cmd, status, label in [
        ("takeover", "human_takeover", "Agent is now silent. You have control."),
        ("resume",   "active",         "Agent has resumed auto-replies."),
        ("close",    "completed",      "Case closed. Agent has exited."),
        ("lookup",   None,             ""),
    ]:
        if text.lower().startswith(cmd + " ") or text.lower() == cmd:
            name = text[len(cmd):].strip()
            if not name:
                if cmd == "lookup":
                    return {"command": cmd, "message": "Please provide a name. Example: lookup Jane Smith"}
                name = _get_last_alert_name()
                if not name:
                    return {"command": cmd, "message": f"No recent high-priority case found. Specify a name: {cmd} Jane Smith"}

            if status:
                record = set_status(name=name, status=status)
                if not record:
                    return {"command": cmd, "message": f"Client '{name}' not found. Check the name and try again."}
                _, base_id, _ = _get_config()
                url = record_url(base_id, record["id"])
                return {"command": cmd, "name": name, "record": record, "url": url,
                        "message": f"✅ {name} — {label}\n🔗 {url}"}
            else:
                record = find_record_by_name(name)
                if not record:
                    return {"command": cmd, "message": f"Client '{name}' not found."}
                f = record["fields"]
                _, base_id, _ = _get_config()
                url = record_url(base_id, record["id"])
                return {
                    "command": cmd, "name": name, "record": record, "url": url,
                    "message": (
                        f"📋 {f.get('name', '?')}\n"
                        f"📞 {f.get('phone', 'not provided')}\n"
                        f"Case: {f.get('case_type', '?')} | Status: {f.get('status', '?')}\n"
                        f"Priority: {f.get('priority', '?')}\n"
                        f"Channel ID: {f.get('channel_user_id', '?')}\n"
                        f"🔗 {url}"
                    )
                }
    return None
