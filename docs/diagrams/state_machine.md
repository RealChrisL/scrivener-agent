# Agent State Machine

State transitions for a single user's relationship with the agent.

```mermaid
stateDiagram-v2
    [*] --> NewUser : first message arrives\n(no history log)

    NewUser --> Tier1_Silent   : existing-client signals\n(payment confirmed / prior reference /\nappointment reference)
    NewUser --> Tier2_Active   : new inquiry\n(service / fee / process question)
    NewUser --> Tier3_Active   : ambiguous\n(hi / excuse me / vague description)

    Tier1_Silent --> [*] : terminal — Operator handles\ndirectly via OA Manager

    Tier2_Active --> Handover  : Operator sends: takeover {name}
    Tier3_Active --> Handover  : Operator sends: takeover {name}
    Handover --> Tier2_Active  : Operator sends: resume {name}
    Handover --> Closed        : Operator sends: close {name}
    Tier2_Active --> Closed    : Operator sends: close {name}
    Tier3_Active --> Closed    : Operator sends: close {name}

    Closed --> [*] : terminal — agent completely exits\nrecord locked (completed)

    note right of Tier2_Active
        Agent replies
        Guides questionnaire
        Updates CRM each turn
    end note

    note right of Handover
        Agent is silent
        CRM still updated
        Operator uses OA Manager
        status = human_takeover
    end note

    note right of Closed
        All events ignored
        Record locked (completed)
        status = completed
    end note
```

## CRM Status Mapping

| State | `status` field | Agent replies? | CRM updated? |
|-------|----------------|----------------|--------------|
| NewUser / Tier2 / Tier3 (active) | `active` | ✅ | ✅ |
| In-progress case | `in_progress` | ✅ | ✅ |
| Temporarily paused | `paused` | ✅ | ✅ |
| Handover | `human_takeover` | ❌ | ✅ |
| Closed | `completed` | ❌ | ❌ |
| Tier 1 silent (new user) | `human_takeover` | ❌ | ✅ |

## Operator Transitions

Operators control two manual transitions:
- `takeover {name}` → sets status to `human_takeover` (agent goes silent)
- `close {name}` → sets status to `completed` (terminal)

All other transitions (`active`, `in_progress`, `paused`, `resume`) are
handled automatically by the agent based on conversation context.
