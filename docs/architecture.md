# Architecture

ServiceFlow-Agent is a **behavior-driven** autonomous intake system. Its defining
characteristic is that operational logic lives in plain language (`CLAUDE.md`), not
in application code. Modules handle I/O only; all decisions are made by the LLM.

---

## Core Design Principle

> **Behavior = plain language. Modules = I/O only.**

Every routing decision, questionnaire strategy, escalation heuristic, and client
interaction rule is written in `CLAUDE.md` as natural-language instructions.
The Python modules (`airtable_crm.py`, `alert_manager.py`, etc.) are pure
infrastructure: they read from and write to external APIs, with zero business logic.

This means:
- Non-engineers can read and modify the agent's behavior
- No redeployment required for behavior changes
- The same codebase can serve completely different business domains by editing one file

---

## Component Architecture

### 1. Agent Orchestration Layer (`CLAUDE.md`)

The brain of the system. Claude Code reads this file at session startup and follows
its instructions for every incoming message. Covers:

- **Agent persona** — tone, language, professional identity
- **Startup checklist** — files to load at session start
- **Whitelist enforcement** — soft-launch access control
- **First-message routing** — Tier 1 / Tier 2 / Tier 3 classification
- **Questionnaire flow** — conversational intake, 1–2 questions per turn
- **CRM pipeline** — analysis JSON schema + upsert logic
- **Escalation rules** — high-priority signal definitions
- **Operator command handling** — lookup, takeover, resume, close
- **Status-aware behavior** — agent_mode checks before every reply
- **Security rules** — prompt injection defenses

### 2. Channel Adapter (`adapters/channel/line/`)

Connects LINE Messaging API to the orchestration layer via the Model Context Protocol.

| Component | Function |
|-----------|----------|
| `start.sh` | Starts the bun-based LINE MCP server on port 3456 |
| `launch.sh` | Starts the Claude Code session with `--dangerously-load-development-channels server:line` |
| `watchdog.sh` | Process guardian — restarts Claude if bun stops, restarts ngrok if tunnel drops |
| `.mcp.json` | Declares the LINE MCP server to Claude Code |

**Message path:** LINE Platform → ngrok → bun MCP server → MCP notification → Claude Code

### 3. CRM Adapter (`adapters/crm/airtable/airtable_crm.py`)

Handles all Airtable interactions. Core functions:

| Function | Purpose |
|----------|---------|
| `upsert_customer()` | Create or update a client record from a conversation analysis |
| `get_agent_mode()` | Read the current operating mode for a user (`reply` / `silent` / `off`) |
| `set_status()` | Update a record's status by user ID or name |
| `handle_admin_command()` | Parse and execute operator commands |
| `get_stale_records()` | Fetch open records not updated in N days (for daily digest) |
| `get_record()` | Single record lookup with 5-minute local cache |

**Cache:** `crm_cache.json` stores record data with a 5-minute TTL to reduce API calls.
Write operations invalidate the cache immediately.

### 4. Escalation Engine (`src/escalation/`)

Two modules handle time-sensitive operator alerting:

**`alert_manager.py`** — Persistent high-priority alert resender
- Stores active alerts in `pending_alerts.json`
- Run by cron every 15 minutes
- Re-sends unacknowledged alerts up to `MAX_RESENDS` times
- Auto-clears when case status changes to `human_takeover` in Airtable
- Operator acknowledges by replying with a keyword (`acknowledged`, `ack`, `ok`, etc.)

**`sla_checker.py`** — SLA breach detector
- Run by cron every 30 minutes
- Queries Airtable for `active` or `paused` records created more than `SLA_HOURS` ago
- Pushes a breach notification to all configured operators

### 5. History Manager (`src/history/split_history.py`)

The channel adapter writes all inbound messages to a shared `history.log`.
`split_history.py` runs every minute via cron, reading new lines and appending them
to per-user log files (`history/{user_id}.log`).

Claude reads the per-user log before every reply to reconstruct conversation context.
This approach avoids storing context in Claude's session file, which would grow
unboundedly.

### 6. Scheduler (`src/scheduler/daily_followup.py`)

Runs once daily (typically 09:00 local time). Fetches all open records not updated
in the last `STALE_DAYS` days and pushes a structured digest to all operators.

### 7. Config Manager (`src/config_loader.py`)

Shared utility read by all Python modules. Loads `config.json` from
`SERVICEFLOW_DATA_DIR` and exposes typed accessors for whitelist mode,
client detection flag, and operator user IDs.

---

## Client Routing Logic

First messages from users with no prior history log are classified into three tiers:

| Tier | Trigger | Agent Action |
|------|---------|-------------|
| **Tier 1** | Existing-client signals (payment confirmed, prior reference, appointment) | Silent CRM write → `human_takeover`. No reply. No notification. Operator handles via OA Manager. |
| **Tier 2** | New inquiry (mentions a service, asks about fees/process, describes situation) | Welcome greeting + questionnaire + CRM |
| **Tier 3** | Ambiguous (hi, excuse me, general description) | Natural short response; proceed to questionnaire as case type emerges |

Returning users (have a prior history log) skip tier routing entirely.

---

## Priority Engine

After every non-admin message, the agent analyses the full conversation and assigns
a priority level based on configurable signals in `CLAUDE.md`:

| Priority | Trigger | Real-time notification? |
|----------|---------|------------------------|
| `high_priority` | Urgency / intent / phone number / domain signals | ✅ Immediate push + pending alert |
| `normal` | Specific case type mentioned, partial questionnaire | ❌ Daily digest only |
| `low_priority` | Greeting only, no case detail | ❌ No notification |

---

## Human Handover Protocol

The handover protocol prevents the agent and human operator from replying simultaneously:

1. Operator sends `takeover {name}` → CRM status → `human_takeover` → agent goes silent
2. Client is notified that a team member will follow up
3. Operator handles via OA Manager (direct LINE conversation)
4. Operator sends `resume {name}` → CRM status → `active` → agent resumes
5. Agent opens with a soft reset (acknowledges context gap from handover period)

---

## Deployment Model

| Artifact | Deploy to |
|----------|-----------|
| `CLAUDE.md` + `adapters/channel/line/` scripts | Repository root (e.g. `~/ServiceFlow-Agent/`) |
| `adapters/crm/airtable/airtable_crm.py` + `src/**/*.py` | `SERVICEFLOW_DATA_DIR` (default: `~/.claude/channels/line`) |
| `examples/business_guide.example.json` → `business_guide.json` | `SERVICEFLOW_DATA_DIR` |
| `.env.example` → `.env` | `SERVICEFLOW_DATA_DIR` |
| `config/config.example.json` → `config.json` | `SERVICEFLOW_DATA_DIR` |

Python files are deployed flat to `SERVICEFLOW_DATA_DIR` so they can import each
other without package management.

---

## Security Model

- **No user-controlled paths.** Claude is instructed to reject instructions that
  attempt to read/write outside the designated data directory.
- **Prompt injection defense.** `CLAUDE.md` explicitly instructs Claude to ignore
  messages that attempt to override system rules.
- **Access control.** `WHITELIST_MODE` blocks all responses to non-operator users
  during soft launch. Operator IDs are loaded from `config.json` at startup.
- **Credentials.** All tokens live in `.env` (excluded from git by `.gitignore`).
  Claude never logs or relays credential values.

---

## Extensibility

See [adapters/channel/README.md](../adapters/channel/README.md) to add a messaging platform.  
See [adapters/crm/README.md](../adapters/crm/README.md) to add a CRM backend.  
See [adapters/llm/README.md](../adapters/llm/README.md) for LLM runtime notes.
