# Message Handling Flow

End-to-end sequence for a single incoming message.

```mermaid
sequenceDiagram
    participant U  as Chat User
    participant AG as Agent (Claude)
    participant AT as Airtable CRM
    participant OP as Operator

    U->>AG: sends message

    AG->>AG: check WHITELIST_MODE (config.json)
    alt WHITELIST_MODE = true AND user is not admin/developer
        AG-->>AG: silently ignore — no reply, no CRM
    end

    AG->>AT: get_agent_mode(user_id)
    AT-->>AG: mode = off / silent / reply

    alt mode = off  [completed]
        AG-->>AG: silent exit — case is closed
    else mode = silent  [human_takeover]
        AG->>AT: upsert_customer (CRM update only, no reply)
    else mode = reply  [active / new user]
        AG->>AG: read SERVICEFLOW_DATA_DIR/history/{user_id}.log

        alt No history log → new user
            AG->>AG: Tier 1 / Tier 2 / Tier 3 routing
            note over AG: Tier 1: existing-client signals → silent CRM<br/>Tier 2: new inquiry → welcome + questionnaire<br/>Tier 3: ambiguous → natural short reply
        end

        AG->>U: reply via channel

        AG->>AT: upsert_customer (create or update record)
        AT-->>AG: record + was_created

        alt high_priority signal detected
            AG->>OP: LINE push notification 🔴
            AG->>AG: register pending_alerts.json
            note over AG,OP: alert_manager.py resends<br/>every 15 min × max 3
        end
    end
```

## Notes

- **Whitelist check** runs before any CRM write — blocked users generate zero data.
- **agent_mode** is read from Airtable on every message; the 5-minute local cache
  (`crm_cache.json`) keeps latency low.
- **Tier 1** routing is only triggered on the *first* message from a user with no
  existing history log. Returning users always reach the `mode = reply` branch.
- **CRM upsert** runs even in `silent` mode (human_takeover) — the operator can
  always see the latest message in Airtable without the agent replying.
