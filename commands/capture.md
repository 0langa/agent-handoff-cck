---
name: capture
description: Update handoff from current work state.
---

# Agent Handoff: capture

Update the active handoff from current work state by running the CLI from the repository root.

Use the arguments supplied after the slash command as CLI arguments:

```text
agent-handoff capture $ARGUMENTS
```

If `agent-handoff` is not on PATH and this is the plugin source checkout, use:

```text
uv run agent-handoff capture $ARGUMENTS
```

When useful, inspect git status and recent commands first, then pass concise `--done`, `--current`, `--next`, `--command`, and `--test` values. Do not capture raw secrets.

- Captures git status and changed files.
- Records commands and tests run.
- Adds progress, decisions, constraints.
- Captures capabilities used.
- Updates `.handoff/active.json`, `.handoff/active.md`, and adds history snapshot.

## Safety

- Does not capture `.env` or secret values.
- Redacts token-like strings in command outputs.
