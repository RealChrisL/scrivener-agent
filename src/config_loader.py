"""
Shared config loader for ServiceFlow-Agent.
Reads config.json from SERVICEFLOW_DATA_DIR (default: ~/.claude/channels/line).
All Python modules should import from here rather than hardcoding paths.
"""
import json
import os

DATA_DIR = os.environ.get("SERVICEFLOW_DATA_DIR", os.path.expanduser("~/.claude/channels/line"))
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise RuntimeError(
            f"config.json not found at {CONFIG_PATH}. "
            "Copy config/config.example.json to that path and fill in your values."
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_notify_user_ids() -> list[str]:
    """Return channel user IDs for admin and developer (used for push notifications)."""
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


def is_returning_client_detection() -> bool:
    """When True, the agent applies Tier 1 routing for returning client signals."""
    return load_config().get("EXISTING_CLIENT_DETECTION", True)
