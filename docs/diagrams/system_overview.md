# System Overview

High-level component diagram for ServiceFlow-Agent.

```mermaid
graph TD
    U[Chat User]          -->|message| LP[LINE Platform]
    LP                    -->|webhook POST| MCP[bun MCP Server\nport 3456 via ngrok]
    MCP                   -->|MCP notification| CC[Claude Code Session\nCLAUDE.md = behavior spec]

    CC -->|reads| HL[Per-user history log\nSERVICEFLOW_DATA_DIR/history/]
    CC -->|get_agent_mode| AT[(Airtable CRM)]
    CC -->|upsert_customer| AT
    CC -->|reply tool| MCP
    MCP -->|push| LP
    LP  -->|deliver| U

    CC  -->|LINE push API| OP[Operator + Developer]

    NG[ngrok]             -->|tunnel :3456| LP
    WD[watchdog.sh]       -->|monitors + restarts| MCP
    WD                    -->|monitors + restarts| NG

    CR1[cron every 1 min]    -->|split_history.py|  HL
    CR2[cron every 15 min]   -->|alert_manager.py|  OP
    CR3[cron daily 09:00]    -->|daily_followup.py| OP
    CR4[cron every 30 min]   -->|sla_checker.py|    OP

    style CC  fill:#f0f4ff,stroke:#4a6fa5
    style AT  fill:#e8f5e9,stroke:#388e3c
    style OP  fill:#fff8e1,stroke:#f9a825
    style MCP fill:#fce4ec,stroke:#c62828
```

## Component Descriptions

| Component | Role |
|-----------|------|
| **Claude Code Session** | The intelligence layer. Reads `CLAUDE.md` at startup, processes every incoming message, decides routing/response/CRM action. |
| **bun MCP Server** | Receives LINE webhooks, translates them into MCP notifications for Claude, and calls the LINE reply API on Claude's behalf. |
| **ngrok** | Exposes the local bun server to the public internet so LINE can reach it via webhook. |
| **Airtable CRM** | Persistent record store. Each user gets one record updated on every interaction. |
| **watchdog.sh** | Ensures bun + ngrok stay alive. Restarts Claude if the MCP server stops responding. |
| **split_history.py** | Reads the shared `history.log` and fans out lines into per-user log files for Claude's conversation context. |
| **alert_manager.py** | Re-sends high-priority notifications every 15 minutes (max 3×) until acknowledged or the case is taken over. |
| **daily_followup.py** | Morning digest of stale open cases pushed to the operator. |
| **sla_checker.py** | Alerts the operator if any case has gone unresponded beyond `SLA_HOURS`. |
