# Escalation Pipeline

How incoming messages are prioritised and how high-priority alerts are managed.

```mermaid
flowchart TD
    MSG[Incoming message] --> WL{WHITELIST_MODE?}

    WL -->|true| WLTEST{admin or\ndeveloper?}
    WLTEST -->|no|  IGNORE[silently ignore]
    WLTEST -->|yes| MODE

    WL -->|false| MODE{agent_mode?}

    MODE -->|off|    EXIT[silent exit\ncase completed]
    MODE -->|silent| CRMONLY[upsert CRM only\nno reply]
    MODE -->|reply|  TIER{Tier routing}

    TIER -->|Tier 1 signals| T1[CRM: human_takeover\nagent silent permanently\nno operator notification]
    TIER -->|Tier 2| T2[welcome greeting\n+ questionnaire]
    TIER -->|Tier 3| T3[natural short reply]

    T2 --> ANALYSE[analyse full conversation\nproduce analysis JSON]
    T3 --> ANALYSE
    T1 --> CRMONLY

    ANALYSE --> PRIO{Priority?}

    PRIO -->|urgent / phone / deadline\ncustom urgency signals| HIGH[high_priority\nimmediate push to Operator]
    PRIO -->|specific case type\npartial questionnaire| MED[normal\ndaily digest only]
    PRIO -->|greeting only\nno case detail| LOW[low_priority\nno real-time notify]

    HIGH --> PUSH[LINE push to all\noperator + developer]
    HIGH --> REG[register pending_alerts.json]
    HIGH --> UPSERT[upsert Airtable]
    MED  --> UPSERT
    LOW  --> UPSERT

    REG --> CRON[alert_manager.py cron\nevery 15 min]
    CRON --> RESEND{send_count\n< MAX_RESENDS?}
    RESEND -->|yes, and interval elapsed| PUSH
    RESEND -->|no — max reached|         AUTOCLEAR[auto-clear alert]

    PUSH --> OPCHECK{Operator\nreplies?}
    OPCHECK -->|acknowledged / ack / ok| CLEARALL[clear_all_alerts]
    OPCHECK -->|takeover command|        CLEARALL
```

## Priority Signal Categories

Configure these in `CLAUDE.md` under `### high_priority signal list`:

| Category | Example signals |
|----------|----------------|
| **Strong intent** | "ready to proceed", "want to hire", "need this done" |
| **Urgency** | "urgent", "asap", "deadline today / this week" |
| **Contact provided** | Phone number (any format), name + phone together |
| **Commitment** | "schedule a call", "book an appointment" |
| **Domain urgency** | Customize for your service area (court date, expiry, etc.) |

## Alert Lifecycle

1. High-priority signal detected → `add_alert(user_id, message)` → `pending_alerts.json`
2. `alert_manager.py` runs every 15 minutes via cron
3. Re-sends up to `MAX_RESENDS` (default: 3) times
4. Auto-clears after max resends, or when:
   - Operator replies with an acknowledgment keyword
   - Case status changes to `human_takeover` in Airtable

## Tier 1 vs High-Priority

| Signal type | Action |
|-------------|--------|
| Tier 1 (existing client, e.g. "payment confirmed") | Silent CRM → `human_takeover`. **No** notification. |
| High-priority (intent/urgency/phone) | Immediate push notification to operator. |

Tier 1 always overrides high-priority — a message with both signals (rare) is treated as Tier 1.
