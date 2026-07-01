---
name: resume
description: Continue from latest handoff.
---

# Agent Handoff: resume

Continue from the latest handoff by running the CLI from the repository root and then following the printed continuation context.

Use the arguments supplied after the slash command as CLI arguments:

```text
agent-handoff resume $ARGUMENTS
```

If `agent-handoff` is not on PATH and this is the plugin source checkout, use:

```text
uv run agent-handoff resume $ARGUMENTS
```

If capability warnings are printed, respect the fallback instructions before continuing.

- Reads `.handoff/active.json`.
- Validates schema.
- Checks current provider against required capabilities.
- Prints continuation summary from `.handoff/active.md`.
- Stops if a required capability is blocked and no fallback exists.
