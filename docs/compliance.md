# Privacy, Legal & Compliance

This document outlines privacy and legal considerations for operators deploying
ServiceFlow-Agent. **Operators are solely responsible for compliance with all
applicable laws and platform terms in their jurisdiction.**

---

## 1. What Data the System Processes

ServiceFlow-Agent processes and stores the following data on the **operator's infrastructure**:

| Data | Where stored | Retention |
|------|-------------|-----------|
| Inbound message text | `SERVICEFLOW_DATA_DIR/history.log` and `history/{user_id}.log` | Indefinite (no automatic purge) |
| Channel user IDs | `history/` filenames + Airtable `channel_user_id` field | Indefinite |
| Names, phone numbers | Airtable CRM fields (if provided by the user) | Operator-controlled |
| Conversation summaries | Airtable CRM fields | Operator-controlled |
| Media files (images, docs) | `SERVICEFLOW_DATA_DIR/inbox/` | Operator-controlled |
| CRM analysis (priority, case type, etc.) | Airtable | Operator-controlled |

**Anthropic (Claude API):** Message content is sent to Anthropic's API for inference.
Refer to [Anthropic's privacy policy](https://www.anthropic.com/privacy) for how
Claude API data is handled.

---

## 2. AI Identity Disclosure

Many jurisdictions require that users be informed when they are communicating with
an AI system, particularly when they sincerely ask whether they are talking to a human.

**Examples of applicable regulations:**
- **EU AI Act** — transparency obligations for AI systems interacting with natural persons
- **FTC Act (US)** — prohibition on deceptive practices, including AI impersonation
- **Taiwan Consumer Protection Act** — disclosure requirements for AI services

**Recommended behavior** (already in the default `CLAUDE.md`):
When a user sincerely asks whether they are talking to a human or an AI, the agent
discloses its AI nature clearly and explains that human follow-up is available.

**Operators must not** configure the agent to deny being an AI when directly asked.

---

## 3. CRM Data Retention

ServiceFlow-Agent does **not** implement automatic data deletion. Operators are
responsible for:

- Defining a data retention policy appropriate for their jurisdiction and business type
- Periodically purging stale Airtable records and local history logs
- Responding to user deletion requests (e.g. GDPR right to erasure, CCPA right to delete)

To delete a user's data, operators must manually:
1. Delete or anonymize the Airtable record
2. Remove `SERVICEFLOW_DATA_DIR/history/{user_id}.log`
3. Remove any media files in `SERVICEFLOW_DATA_DIR/inbox/`

---

## 4. PII Handling

**At rest:**
- History logs and media files are stored as plain text/binary on the operator's server.
  No encryption at rest is provided by this framework — operators should use filesystem
  encryption or a secrets manager in regulated environments.
- Airtable encrypts data at rest by default (refer to Airtable's security documentation).

**In transit:**
- All communication with Airtable, LINE, and the Claude API uses HTTPS/TLS.
- Local traffic between Claude Code and the bun MCP server is over localhost.

**Recommendations for regulated industries (healthcare, legal, finance):**
- Restrict server access to authorized personnel only
- Enable audit logging at the infrastructure level
- Consider a self-hosted CRM adapter instead of Airtable for sensitive data

---

## 5. Messaging Platform Responsibilities

Operators using the LINE Messaging API must comply with:
- [LINE Messaging API Terms of Use](https://terms2.line.me/LINE_Developers_Agreement)
- LINE's data handling and user consent requirements
- Any local regulations governing commercial messaging (e.g. opt-in requirements)

Operators porting this framework to other platforms (WhatsApp, Telegram, etc.) must
independently review and comply with those platforms' terms of service.

---

## 6. Third-Party APIs

This framework integrates with the following third-party services. Operators are
subject to each provider's terms:

| Service | Purpose | Terms |
|---------|---------|-------|
| Anthropic Claude API | LLM inference | [anthropic.com/terms](https://www.anthropic.com/legal/consumer-terms) |
| LINE Messaging API | Channel adapter | [developers.line.biz](https://developers.line.biz/en/docs/line-login/terms/) |
| Airtable API | CRM adapter | [airtable.com/tos](https://www.airtable.com/company/tos) |
| ngrok | Webhook tunnel | [ngrok.com/tos](https://ngrok.com/tos) |

---

## 7. Credential Security

API tokens and secrets are stored in `SERVICEFLOW_DATA_DIR/.env`.

**Operators must:**
- Never commit `.env` to version control (`.gitignore` already excludes it)
- Restrict read access to `.env` (`chmod 600 ~/.claude/channels/line/.env`)
- Use short-lived tokens with minimal required scopes where supported
- Rotate tokens immediately if a breach is suspected

For production deployments, consider using a secrets manager (AWS Secrets Manager,
HashiCorp Vault, etc.) and loading credentials at runtime rather than storing them
in flat files.

---

## 8. GDPR / CCPA / PDPA Considerations

If your users are located in the EU (GDPR), California (CCPA), Thailand (PDPA),
or other regions with data protection legislation, you may need to:

- Provide a privacy notice informing users that their messages are processed by AI
- Obtain consent before collecting personal data (name, phone, etc.)
- Honor subject access requests (provide a copy of stored data upon request)
- Honor deletion requests (erase stored data upon request)
- Appoint a Data Protection Officer if required by your jurisdiction
- Conduct a Data Protection Impact Assessment (DPIA) for high-risk processing

**This framework does not provide compliance tooling for these requirements.**
Operators must build or bolt on the necessary workflows.

---

## 9. Operator Responsibility Statement

ServiceFlow-Agent is a software framework. It is provided "as is" under the MIT
License without warranties of any kind. The framework authors:

- Do **not** provide legal, privacy, or compliance advice
- Are **not** responsible for how operators configure or deploy the system
- Are **not** liable for any data breaches, regulatory violations, or user harms
  arising from operator deployments

Before going live with real users, operators should:
1. Consult qualified legal counsel regarding applicable regulations
2. Review and understand all third-party API terms
3. Implement appropriate data governance policies
4. Test the agent's behavior thoroughly, including edge cases

---

*For questions about the framework itself, open an issue on GitHub.*  
*For legal and compliance questions, consult a qualified attorney in your jurisdiction.*
