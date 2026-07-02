# Agent Handoff (`agent-handoff-cck`)

Cross-agent handoff plugin for Codex, Claude Code, and Kimi Code.

## Goal

Let any of the three agents continue work started by another without losing task state, safety context, capability requirements, or next actions.

## Install

```bash
pip install -e .
# or with uv
uv pip install -e .
```

## CLI

```bash
agent-handoff init --title "Fix auth" --objective "Resolve token expiry" --provider codex
agent-handoff capture --provider codex --done "reproduced" --next "patch middleware"
agent-handoff status
agent-handoff verify --provider claude-code
agent-handoff export claude-code
agent-handoff resume --provider claude-code
agent-handoff close --provider claude-code
```

You can also run via `python -m agent_handoff` or `uv run agent-handoff`.

## Provider Manifests

| Provider    | Manifest                     |
|-------------|------------------------------|
| Codex       | `.codex-plugin/plugin.json`  |
| Claude Code | `.claude-plugin/plugin.json` |
| Kimi Code   | `kimi.plugin.json`           |

All three manifests share the same plugin name and version. Codex and Kimi use explicit skill/command paths; Claude Code validates explicit `skills` and `commands` paths and auto-discovers the default `agents/` directory.

## Provider Workflows

### Codex

Install the plugin from the Codex plugin UI by pointing it at this local repository, or use the CLI fallback directly:

```text
@agent-handoff capture current task
@agent-handoff resume latest handoff
@agent-handoff export claude-code
```

Or directly via CLI:

```bash
agent-handoff init --title "..." --objective "..." --provider codex
agent-handoff capture --provider codex --done "step A" --next "step B"
agent-handoff export claude-code
```

Codex-specific: record provider-bound connectors (Gmail, GitHub) as capabilities with fallback entries so Claude/Kimi know what they cannot rerun.

### Claude Code

Install the plugin from a local path. Slash commands become available when the client discovers `commands/`:

```text
/handoff:init --title "..." --objective "..."
/handoff:capture --done "step A" --next "step B"
/handoff:status
/handoff:verify
/handoff:export codex
/handoff:resume
/handoff:close
```

Or directly via CLI:

```bash
agent-handoff init --title "..." --objective "..." --provider claude-code
agent-handoff capture --provider claude-code
agent-handoff verify --provider claude-code
agent-handoff export codex
```

Claude Code agents (`handoff-verifier`, `handoff-summarizer`) are available through the default `agents/` directory discovery.

### Kimi Code

Install the plugin from a local path or GitHub URL:

```text
/plugins install C:\Users\...\agent-handoff-cck
```

After installation and `/reload`, commands are namespaced:

```text
/agent-handoff:init --title "..." --objective "..."
/agent-handoff:capture --done "step A" --next "step B"
/agent-handoff:status
/agent-handoff:verify
/agent-handoff:export codex
/agent-handoff:resume
/agent-handoff:close
```

Or directly via CLI:

```bash
agent-handoff init --title "..." --objective "..." --provider kimi-code
agent-handoff capture --provider kimi-code
agent-handoff export claude-code
```

## Files Produced

```text
.handoff/
  active.json       — canonical machine-readable handoff
  active.md         — human-readable fallback (pasteable into any agent)
  history/          — immutable timestamped snapshots
  exports/          — provider-specific continuation prompts
  attachments/      — optional diffs and logs (opt-in)
```

## Handoff Schema

The handoff artifact (`active.json`) includes:

- **task** — title, objective, status
- **providers** — creator, last updater, compatible providers
- **context** — repo root, important files, constraints, decisions, open questions
- **progress** — done, current, next, blockers
- **workspace** — git status, changed files, commands run, tests run
- **capabilities** — used, required next, missing at capture, fallbacks
- **safety** — secrets touched, sensitive sources, destructive actions, user approvals, privacy notes
- **resume** — summary, recommended next provider, next prompt

The full JSON Schema is at `schemas/handoff.schema.json`.

## Capability Fallbacks

When a capability is provider-bound (e.g., Codex Gmail connector), record a fallback:

| Fallback type       | Meaning                                         |
|---------------------|--------------------------------------------------|
| `captured-result`   | Enough data in handoff; no rerun needed          |
| `manual-user-input` | User must paste/export data                      |
| `switch-provider`   | Resume in provider that has the tool             |
| `local-equivalent`  | Use shell/MCP/API equivalent                     |
| `skip-safe`         | Optional step                                    |
| `blocked`           | Cannot continue safely                           |

## Safety

- `.env`, tokens, keys, and raw private data are never captured.
- Secrets are redacted from command output.
- Sensitive sources are listed by category, not by content.
- Destructive actions require explicit recording and user approval flags.

## Tests

```bash
uv sync --extra dev
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE).
