# Deployment Topology

Runtime environment for the ServiceFlow-Agent LINE adapter.

```mermaid
graph TB
    subgraph HOST["Host Machine (VPS / local server)"]
        subgraph TMUX["tmux sessions"]
            TS1["line-agent\nclaude --dangerously-skip-permissions\n--continue server:line"]
            TS2["watchdog\nbash adapters/channel/line/watchdog.sh"]
            TS3["ngrok\nngrok http 3456"]
        end

        BUN["bun process\nLINE MCP Server :3456"]
        CRON["cron jobs\n• split_history.py  every 1 min\n• alert_manager.py  every 15 min\n• daily_followup.py daily 09:00\n• sla_checker.py    every 30 min"]

        subgraph DATADIR["SERVICEFLOW_DATA_DIR\n(~/.claude/channels/line)"]
            ENV[".env\nAPI tokens"]
            CFG["config.json\nroles, flags"]
            BG["business_guide.json\nservice areas"]
            HL["history/\nper-user .log files"]
            CACHE["crm_cache.json\n5-min Airtable cache"]
            ALERTS["pending_alerts.json\nhigh-priority alert queue"]
        end

        subgraph REPO["Repository Root\n(~/ServiceFlow-Agent)"]
            CLAUSEMD["CLAUDE.md\nbehavior spec"]
            PYMOD["Python modules\n(deployed from src/ + adapters/crm/)"]
        end
    end

    subgraph EXTERNAL["External Services"]
        LINE["LINE Platform\napi.line.me"]
        AIRTABLE["Airtable API\nairtable.com"]
        ANTHROPIC["Claude API\napi.anthropic.com"]
    end

    PHONE["User's Phone"] -->|LINE message| LINE
    LINE -->|webhook POST /webhook| TS3
    TS3 -->|tunnel :3456| BUN
    BUN -->|MCP notification| TS1
    TS1 -->|reply tool| BUN
    BUN -->|push message| LINE
    LINE -->|deliver| PHONE

    TS1 -->|reads| CLAUSEMD
    TS1 -->|reads/writes| DATADIR
    TS1 -->|REST API| AIRTABLE
    TS1 -->|inference| ANTHROPIC

    TS2 -->|monitors + restarts| BUN
    TS2 -->|monitors + restarts| TS3

    CRON -->|reads/writes| DATADIR
    CRON -->|push messages| LINE
    CRON -->|reads| AIRTABLE

    OPPHONE["Operator's Phone"] -->|LINE DM| LINE
```

## Port and Network Summary

| Component | Port | Notes |
|-----------|------|-------|
| bun MCP Server | 3456 (default) | Local only; exposed via ngrok |
| ngrok tunnel | 4040 (admin API) | ngrok HTTPS URL registered as LINE webhook |
| Airtable API | 443 (HTTPS) | Outbound from host |
| LINE API | 443 (HTTPS) | Outbound from host |
| Claude API | 443 (HTTPS) | Outbound from host |

## Scaling Notes

- **Single-node by design.** The Claude Code session is stateful (uses `--continue`),
  so horizontal scaling requires session affinity or an external state store.
- **VPS recommendation.** A 2 vCPU / 2 GB RAM instance is sufficient for most
  professional services deployments (< 1000 clients).
- **Production hardening.** Replace ngrok with a proper reverse proxy (nginx + SSL cert)
  and set `LINE_WEBHOOK_PORT` to an internally-accessible port.
