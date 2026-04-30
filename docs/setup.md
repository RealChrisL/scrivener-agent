# Setup Guide

This guide walks through a full deployment of ServiceFlow-Agent with the LINE channel
adapter and Airtable CRM adapter. Allow 30–60 minutes for a first-time setup.

---

## Prerequisites

| Dependency | Version | Install |
|-----------|---------|---------|
| [Claude Code CLI](https://claude.ai/code) | Latest | `npm install -g @anthropic-ai/claude-code` |
| [Bun](https://bun.sh) | 1.0+ | `curl -fsSL https://bun.sh/install \| bash` |
| [Python](https://python.org) | 3.10+ | System package manager |
| [tmux](https://github.com/tmux/tmux) | Any | `apt install tmux` / `brew install tmux` |
| [ngrok](https://ngrok.com) | Latest | `apt install ngrok` / download from ngrok.com |
| [LINE Developers account](https://developers.line.biz) | — | Free signup |
| [Airtable account](https://airtable.com) | — | Free tier sufficient |

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/your-org/ServiceFlow-Agent.git
cd ServiceFlow-Agent
```

---

## Step 2 — Configure Environment Variables

```bash
# Create the data directory
mkdir -p ~/.claude/channels/line

# Copy the credentials template
cp .env.example ~/.claude/channels/line/.env

# Edit with your actual credentials
nano ~/.claude/channels/line/.env
```

Fill in all four values:

```
LINE_CHANNEL_ACCESS_TOKEN=   # From LINE Developers → Messaging API → Channel Access Token
LINE_CHANNEL_SECRET=         # From LINE Developers → Basic Settings → Channel Secret
AIRTABLE_API_TOKEN=          # From airtable.com/account → API → Personal access token
AIRTABLE_BASE_ID=            # From your base's API docs URL (starts with "app")
```

Protect the file:
```bash
chmod 600 ~/.claude/channels/line/.env
```

---

## Step 3 — Set Up Airtable

Create a table named `client_records` (or set `TABLE_NAME` in `.env` to your preferred name)
with the following fields. The exact field names matter — they must match what's in `config/crm_schema.example.json`.

| Field name | Field type |
|-----------|-----------|
| `channel_user_id` | Single line text |
| `name` | Single line text |
| `gender` | Single select: `male` / `female` / `unknown` |
| `phone` | Phone number |
| `case_type` | Single select — add your service area names + `other` |
| `summary` | Long text |
| `client_type` | Single select: `urgent` / `proactive` / `exploratory` / `watching` |
| `priority` | Single select: `high_priority` / `normal` / `low_priority` |
| `priority_reason` | Long text |
| `status` | Single select: `active` / `in_progress` / `paused` / `human_takeover` / `completed` |
| `action_items` | Long text |
| `conversation_summary` | Long text |
| `client_scenario` | Long text |
| `questionnaire_summary` | Long text |
| `first_contact_at` | Date (include time, UTC) |
| `last_interaction_at` | Date (include time, UTC) |

After creating the table, update `TABLE_ID` in `adapters/crm/airtable/airtable_crm.py`
with the table ID from your Airtable URL.

---

## Step 4 — Deploy Runtime Library

Copy Python modules to the data directory so they can import each other:

```bash
# CRM adapter
cp adapters/crm/airtable/airtable_crm.py ~/.claude/channels/line/

# Supporting modules
cp src/config_loader.py ~/.claude/channels/line/
cp src/escalation/alert_manager.py ~/.claude/channels/line/
cp src/escalation/sla_checker.py ~/.claude/channels/line/
cp src/history/split_history.py ~/.claude/channels/line/
cp src/scheduler/daily_followup.py ~/.claude/channels/line/
cp src/test_scenarios.py ~/.claude/channels/line/
```

Or use the one-liner:
```bash
cp adapters/crm/airtable/airtable_crm.py src/config_loader.py \
   src/escalation/alert_manager.py src/escalation/sla_checker.py \
   src/history/split_history.py src/scheduler/daily_followup.py \
   src/test_scenarios.py \
   ~/.claude/channels/line/
```

---

## Step 5 — Create config.json

```bash
cp config/config.example.json ~/.claude/channels/line/config.json
nano ~/.claude/channels/line/config.json
```

Fill in:

```json
{
  "WHITELIST_MODE": true,
  "EXISTING_CLIENT_DETECTION": true,
  "firm_name": "Your Firm Name",
  "team_name": "Your Team Name",
  "roles": {
    "developer": "YOUR_LINE_USER_ID",
    "admin": "OPERATOR_LINE_USER_ID"
  }
}
```

To find a LINE user ID: send any message to your OA after launch, then check
`~/.claude/channels/line/history.log` — each line contains `[user:<user_id>]`.

---

## Step 6 — Configure business_guide.json

```bash
cp examples/business_guide.example.json ~/.claude/channels/line/business_guide.json
nano ~/.claude/channels/line/business_guide.json
```

Replace each `[placeholder]` with your firm's actual service areas, questions,
pricing, and processes. The agent loads this file at startup.

---

## Step 7 — Customize CLAUDE.md

Open `CLAUDE.md` and replace the template placeholders:
- `{{YOUR_FIRM_NAME}}` — your firm's public-facing name
- `{{YOUR_TEAM_NAME}}` — your team name for internal messages
- The high-priority signal list — add urgency signals relevant to your service domain
- The Tier 1 existing-client signal list — add signals typical of your returning clients

---

## Step 8 — Install LINE MCP Plugin

```bash
claude mcp add claude-line-channel
```

Verify the plugin path and update `adapters/channel/line/.mcp.json` if the
detected path differs from what's in the file. Also copy `.mcp.json` and
`.claude/settings.local.json` to your deploy directory if running from a
different path than the repo root.

---

## Step 9 — Set Up Cron Jobs

```bash
crontab -e
```

Add these entries (adjust `SERVICEFLOW_DATA_DIR` path if you changed it):

```cron
# Fan out shared history to per-user log files (every minute)
* * * * * python3 ~/.claude/channels/line/split_history.py >> ~/.claude/channels/line/history/.split.log 2>&1

# Resend unacknowledged high-priority alerts (every 15 minutes)
*/15 * * * * python3 ~/.claude/channels/line/alert_manager.py >> ~/.claude/channels/line/alert.log 2>&1

# Daily stale-case digest at 09:00 local time
# Adjust UTC offset: Taiwan/Singapore = 01:00 UTC, US Eastern = 14:00 UTC
30 1 * * * python3 ~/.claude/channels/line/daily_followup.py >> ~/.claude/channels/line/followup.log 2>&1

# SLA breach check (every 30 minutes)
*/30 * * * * python3 ~/.claude/channels/line/sla_checker.py >> ~/.claude/channels/line/sla.log 2>&1
```

---

## Step 10 — Launch

```bash
# Start the process guardian in the background (keeps bun + ngrok alive)
tmux new-session -d -s watchdog "bash adapters/channel/line/watchdog.sh"

# Start the agent (stays in foreground so you can watch the logs)
tmux new-session -s line-agent "bash adapters/channel/line/launch.sh"
```

Check that everything is running:
```bash
tmux ls
# Should show: line-agent, watchdog, ngrok
```

---

## Step 11 — Go Live

1. In [LINE Developers console](https://developers.line.biz), go to your channel → Messaging API
2. Set the **Webhook URL** to: `https://<your-ngrok-url>/webhook`
3. Enable **Use webhook**
4. Disable **Auto-reply messages**
5. Test by sending a message to your OA from your personal LINE account
6. Check `~/.claude/channels/line/history.log` to confirm the message was received

When ready to open to the public:
```bash
# Edit config.json
nano ~/.claude/channels/line/config.json
# Set "WHITELIST_MODE": false
```

Or send `emergency_close` to the agent to re-enable whitelist mode at any time.

---

## Troubleshooting

**Agent not responding to messages:**
- Check `tmux attach -t line-agent` for errors
- Verify the webhook URL in LINE Developers console matches your current ngrok URL
- `curl https://<ngrok-url>/webhook` should return a response

**CRM records not appearing in Airtable:**
- Confirm `AIRTABLE_API_TOKEN` and `AIRTABLE_BASE_ID` are correct in `.env`
- Check that all field names in Airtable exactly match `config/crm_schema.example.json`
- Test manually: `cd ~/.claude/channels/line && python3 -c "from airtable_crm import get_record; print(get_record('test'))"`

**ngrok tunnel keeps dropping:**
- Free ngrok accounts have session limits — consider upgrading or using a static domain
- `watchdog.sh` will restart ngrok automatically; update the LINE webhook URL after each restart
- For production, replace ngrok with a proper reverse proxy

**`split_history.py` not creating per-user logs:**
- Confirm the cron job is running: `crontab -l`
- Check `~/.claude/channels/line/history/.split.log` for errors
- Verify `history.log` exists and is being written to

**How to find a user's LINE ID:**
- After they send a message, look in `~/.claude/channels/line/history.log` for `[user:<id>]`
- Or send `lookup <name>` to the agent after their record is created in Airtable
