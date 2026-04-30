# CRM Adapters

A **CRM adapter** handles all read/write operations against an external CRM or database.
It provides the interface that the ServiceFlow-Agent orchestration layer uses to persist
client records, check agent mode, and execute operator commands.

## Current Implementations

| CRM | Status | Directory |
|-----|--------|-----------|
| Airtable | ✅ Production-ready | `airtable/` |
| Google Sheets | 🗺️ Planned | — |
| HubSpot CRM | 🗺️ Planned | — |
| Notion Database | 🗺️ Planned | — |

## Airtable Adapter

Uses the Airtable REST API directly (no third-party SDK — stdlib `urllib` only).
Includes a 5-minute local cache (`crm_cache.json`) to reduce API calls.

**File:** `airtable/airtable_crm.py`

**Required env vars:** `AIRTABLE_API_TOKEN`, `AIRTABLE_BASE_ID`  
**Optional env var:** `TABLE_NAME` (default: `client_records`)

**Field schema:** See `config/crm_schema.example.json`.

## Required Interface

Any CRM adapter must expose these functions so that `CLAUDE.md` code snippets and
the scheduler/escalation modules can call them:

```python
def upsert_customer(user_id: str, analysis: dict) -> tuple[dict, bool]:
    """Create or update a record. Returns (record, was_created)."""

def get_agent_mode(user_id: str) -> str:
    """Return 'reply', 'silent', or 'off' based on CRM status."""

def set_status(user_id=None, name=None, status: str = "") -> dict | None:
    """Set the status field by user ID or name."""

def handle_admin_command(text: str) -> dict | None:
    """Parse and execute operator commands. Returns result dict or None."""

def get_record(user_id: str) -> dict | None:
    """Return a single record by channel_user_id, or None."""

def get_stale_records(days: int) -> list[dict]:
    """Return records not updated in the last N days (excluding completed)."""

def record_url(base_id: str, record_id: str) -> str:
    """Return a browser URL to the record."""
```

## Building a New CRM Adapter

1. Create `adapters/crm/<platform>/crm.py` implementing the interface above
2. Map the standard field names (`name`, `phone`, `status`, `priority`, etc.) to
   your platform's field equivalents
3. Update `CLAUDE.md` to `import` from your new module instead of `airtable_crm`
4. Add any new credentials to `.env.example`
5. Document your field mapping in a `README.md` in your adapter directory
