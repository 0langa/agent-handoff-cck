---
name: close
description: Mark task complete and archive.
---

# Agent Handoff: close

Mark the task complete and archive the active handoff by running the CLI from the repository root.

Use the arguments supplied after the slash command as CLI arguments:

```text
agent-handoff close $ARGUMENTS
```

If `agent-handoff` is not on PATH and this is the plugin source checkout, use:

```text
uv run agent-handoff close $ARGUMENTS
```

Only close the handoff when the user has finished the task or explicitly asks to close it.

- Sets status to `complete`.
- Adds final history snapshot.
- Removes `.handoff/active.json` and `.handoff/active.md`.
- Leaves external memory sync to a future integration.
