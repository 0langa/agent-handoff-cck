---
name: export
description: Generate continuation prompt for target provider.
---

# Agent Handoff: export

Generate a continuation prompt for a target provider by running the CLI from the repository root.

Use the arguments supplied after the slash command as CLI arguments:

```text
agent-handoff export $ARGUMENTS
```

If `agent-handoff` is not on PATH and this is the plugin source checkout, use:

```text
uv run agent-handoff export $ARGUMENTS
```

If no target is supplied, ask which target to export: `codex`, `claude-code`, `kimi-code`, or `generic`.

- `.handoff/exports/codex.md`
- `.handoff/exports/claude-code.md`
- `.handoff/exports/kimi-code.md`
- `.handoff/exports/unknown.md` (for generic)

## Content

Each export includes role-specific instructions, objective, status, next actions, capability warnings, safety constraints, file paths, and tests run.
