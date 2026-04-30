"""
Shared config loader — reads ~/.claude/channels/line/config.json.
All Python scripts should import from here instead of hardcoding user IDs.
"""
import json
import os

CONFIG_PATH = os.path.expanduser("~/.claude/channels/line/config.json")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise RuntimeError(f"config.json not found at {CONFIG_PATH}. Copy config.example.json and fill in your values.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_notify_user_ids() -> list[str]:
    cfg = load_config()
    roles = cfg.get("roles", {})
    ids = []
    if roles.get("admin"):
        ids.append(roles["admin"])
    if roles.get("developer"):
        ids.append(roles["developer"])
    return ids


def get_developer_id() -> str:
    return load_config().get("roles", {}).get("developer", "")


def get_admin_id() -> str:
    return load_config().get("roles", {}).get("admin", "")


def is_whitelist_mode() -> bool:
    return load_config().get("WHITELIST_MODE", True)


def is_existing_client_detection() -> bool:
    return load_config().get("EXISTING_CLIENT_DETECTION", True)
