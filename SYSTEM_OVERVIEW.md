<div align="right">

🌐 **English** | [繁體中文](SYSTEM_OVERVIEW.zh-TW.md)

</div>

# LINE Agent — System Overview

---

## System Value

- **24/7 fully automatic** new client reception — zero missed contacts
- Smart questionnaire guidance (1–2 questions per round), automatic Airtable CRM record creation
- High-priority cases **immediately notify** the team; low-priority cases summarized in daily digest
- Team only needs to focus on high-value cases — routine triage and record-keeping fully automated

---

## System Modes (edit `CLAUDE.md`)

| Mode | Current Value | Description |
|------|--------------|-------------|
| `WHITELIST_MODE` | `true` | `true` = whitelist mode / `false` = open to public |
| `EXISTING_CLIENT_DETECTION` | `true` | `true` = auto-detect existing clients / `false` = treat all as new |

---

## Client Routing Logic (first message)

| Tier | Trigger | Agent Behavior |
|------|---------|---------------|
| **Tier 1** Existing client | Payment confirmed / "you said last time" / "received your docs" / "what time today" | Silent — CRM recorded (人工接管中), team handles via OA Manager |
| **Tier 2** New client | Inquires about service / fee / process, describes situation from scratch | Welcome message + questionnaire guidance + CRM |
| **Tier 3** Ambiguous | Hi / excuse me / general description | Natural short response; proceed to questionnaire as case type emerges |

**Returning user** (has history log) → reads conversation history, decides response based on `bot_mode`

---

## Notification Architecture

| Type | Trigger | Recipients |
|------|---------|-----------|
| 🔴 High-priority instant notification + quick command | 急 / 委託 / phone number / debt > assets / court notice / deadline approaching | Developer + {{YOUR_TEAM_NAME}} |
| 📋 Daily 08:30 follow-up digest | Scheduled cron (01:00 UTC) | Developer + {{YOUR_TEAM_NAME}} |
| ⏰ Unacknowledged alert resend | Every 15 minutes, max 3 times | Developer + {{YOUR_TEAM_NAME}} |

---

## Command Manual (send via LINE DM)

| Command | Function |
|---------|---------|
| `查 [姓名]` | Look up Airtable client record |
| `接管 [姓名]` | Agent silent + notify client that a team member will follow up (omit name = auto last high-priority alert) |
| `恢復 [姓名]` | Agent resumes auto-replies |
| `結案 [姓名]` | Case complete — agent exits permanently |
| `緊急關閉` | Immediately set WHITELIST_MODE=true in CLAUDE.md |
| `已處理` / `ok` / `好` | Clear all pending alert resends |

---

## Important Notes

1. **Send `接管` before replying via OA Manager** — prevents agent and team member from simultaneously replying to the client
2. **Tier 1 is fully automatic and silent** — no manual action needed; handle directly from OA Manager
3. **「已完成」is a terminal state** — after closing, records are locked and the agent completely exits
4. **Emergency close** — after launch, send `緊急關閉` at any time to immediately return to whitelist mode

---

## Future Development

**Near term**
- Add specific fee figures to `business_guide.json` so the agent can directly answer pricing questions
- Set `WHITELIST_MODE = false` → official public launch

**Medium term**
- Appointment system integration — agent auto-organizes scheduling
- AI fee estimation feature

**Long term**
- Multi-case parallel tracking dashboard
- Client churn warning (auto-reminder when no response for extended period)
- SEO marketing content auto-generation (client scenario descriptions already being auto-built)

---

## System Architecture

| Component | Description |
|----------|-------------|
| LINE Agent | @your_line_oa_handle, driven by Claude Code session |
| Airtable CRM | Auto-filing, 17 fields, including questionnaire / scenario / todos |
| Per-user logs | Per-user conversation records, cron updates every minute |
| Cron jobs | split_history (1 min) / alert_resend (15 min) / daily_followup (08:30 TWN) |
| Test coverage | 53 unit tests ✅ + 6 E2E scenarios ✅ |

---

*Maintained via Claude Code*
