# Contributing to ServiceFlow-Agent

Thank you for your interest in contributing! This guide covers everything you need
to get started, from development setup to submitting a pull request.

---

## Ways to Contribute

- **New channel adapters** — Add support for WhatsApp, Telegram, Webchat, etc.
- **New CRM adapters** — Add HubSpot, Google Sheets, Notion, or custom backends
- **`CLAUDE.md` improvements** — Better routing logic, richer questionnaire templates, stronger security rules
- **Python module improvements** — Performance, reliability, observability
- **Documentation** — Setup guides, examples, translations
- **Bug reports** — Open an issue with reproduction steps
- **Feature requests** — Open an issue describing the use case

---

## Development Setup

```bash
git clone https://github.com/your-org/ServiceFlow-Agent.git
cd ServiceFlow-Agent

# Python 3.10+ required — no pip dependencies
python3 --version

# Copy and fill in your test credentials
cp .env.example /tmp/test-serviceflow/.env
# Edit /tmp/test-serviceflow/.env with real tokens for integration tests

export SERVICEFLOW_DATA_DIR=/tmp/test-serviceflow

# Run the test suite
python3 src/test_scenarios.py
```

---

## Code Style

**Python:**
- Follow PEP 8. Line length ≤ 100 characters.
- Standard library only — do not introduce third-party dependencies.
- Type hints on all public functions.
- Docstrings for module-level and public functions (one line is fine).
- No magic numbers — use named constants.

**Shell scripts:**
- `#!/bin/bash` shebang on all scripts.
- `set -euo pipefail` is not required but is encouraged for new scripts.
- Comment non-obvious lines.
- Environment variables should have sensible defaults (`${VAR:-default}`).

**Markdown:**
- Mermaid diagrams must render on GitHub (test at [mermaid.live](https://mermaid.live)).
- Keep line length ≤ 120 characters for prose.

---

## Adding a Channel Adapter

See [adapters/channel/README.md](adapters/channel/README.md) for the full interface spec.

**Quick checklist:**
1. Create `adapters/channel/<platform>/` with `start.sh`, `launch.sh`, and `.mcp.json`
2. Document environment variables needed in `.env.example`
3. Update `adapters/channel/README.md` with the new adapter's status and docs link
4. Add at least one example conversation in `examples/sample_conversations/`
5. If the adapter introduces a new data directory layout, document it in `docs/setup.md`

---

## Adding a CRM Adapter

See [adapters/crm/README.md](adapters/crm/README.md) for the required interface.

**Quick checklist:**
1. Create `adapters/crm/<platform>/crm.py` implementing all required functions
2. Map standard field names to the platform's equivalents
3. Add a `README.md` in the adapter directory documenting the field mapping
4. Update `adapters/crm/README.md` with the new adapter's status
5. Document credentials in `.env.example`

---

## Pull Request Process

1. **Fork** the repository and create a feature branch: `git checkout -b feat/my-feature`
2. **Write tests** — add test cases to `src/test_scenarios.py` for logic changes
3. **Run tests**: `python3 src/test_scenarios.py` — all must pass
4. **Open a PR** with:
   - A clear description of what changed and why
   - Any relevant issue numbers (`Closes #123`)
   - Notes on backward compatibility if you changed field names or API signatures
5. **Review** — maintainers may request changes; please respond within 14 days

---

## Reporting Issues

When filing a bug report, please include:
- Your Python version (`python3 --version`)
- The Claude Code version (`claude --version`)
- The channel adapter you're using
- Steps to reproduce the issue
- What you expected vs. what happened
- Relevant log output (redact any credentials or PII)

---

## Code of Conduct

Be respectful. Constructive criticism is welcome; personal attacks are not.
This project follows the [Contributor Covenant](https://www.contributor-covenant.org/).

---

*Thank you for helping make ServiceFlow-Agent better for everyone.*
