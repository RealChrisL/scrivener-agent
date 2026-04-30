# Sample Conversations

This directory is for storing example conversation transcripts used in testing
and documentation. They demonstrate how the tier routing, questionnaire flow,
and escalation logic behave in practice.

## Format

Each sample is a JSON file with an array of turns:

```json
[
  { "role": "user",  "text": "Hi, I'd like to ask about your contract review service." },
  { "role": "agent", "text": "Hello! Thanks for reaching out to {{YOUR_FIRM_NAME}}. ..." },
  { "role": "user",  "text": "It's a vendor agreement, about $50k value. How much do you charge?" },
  { "role": "agent", "text": "For a standard vendor agreement of that size, our fee is ..." },
  { "role": "user",  "text": "Great. My number is 555-867-5309, can someone call me?" }
]
```

The final message above contains a phone number — a `high_priority` signal that
triggers an immediate push notification to the operator.

## Running Manual E2E Tests

After deploying the Python modules, you can simulate a full conversation flow:

```bash
cd $SERVICEFLOW_DATA_DIR
python3 test_scenarios.py
```

For Airtable integration tests, ensure `.env` is configured with valid credentials.

## Privacy Notice

**Never commit real customer conversations to this directory.**

- Anonymize all names, phone numbers, and case details in any examples you add
- Use fictional scenarios only
- See [docs/compliance.md](../../docs/compliance.md) for PII handling guidance

## Adding Your Own Examples

1. Create `examples/sample_conversations/my_scenario.json`
2. Use only fictional data
3. Add a brief description comment at the top of the file
4. Reference it in your PR description so reviewers can understand the flow it demonstrates
