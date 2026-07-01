# Agent Continuity (`agent-handoff-cck`)

Cross-agent handoff plugin for Codex, Claude Code, and Kimi Code.

## Goal

Let any of the three agents continue work started by another without losing task state, safety context, or next actions.

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

## Provider manifests

- Codex: `.codex-plugin/plugin.json`
- Claude Code: `.claude-plugin/plugin.json`
- Kimi Code: `kimi.plugin.json`

## Files produced

- `.handoff/active.json` — canonical handoff.
- `.handoff/active.md` — human-readable fallback.
- `.handoff/history/` — snapshots.
- `.handoff/exports/` — provider-specific prompts.

## Safety

- `.env`, tokens, keys, and raw private data are never captured.
- Secrets are redacted from command output.
- Sensitive sources are listed, not their contents.

## Tests

```bash
uv sync --extra dev
uv run pytest
```

## License

MIT
