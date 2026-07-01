---
name: init
description: Create a new handoff record.
---

# Agent Handoff: init

Create a new handoff record by running the CLI from the repository root.

Use the arguments supplied after the slash command as CLI arguments:

```text
agent-handoff init $ARGUMENTS
```

If `agent-handoff` is not on PATH and this is the plugin source checkout, use:

```text
uv run agent-handoff init $ARGUMENTS
```

If required arguments are missing, ask for the missing title/objective/provider instead of inventing them.

- Creates `.handoff/active.json` and `.handoff/active.md`.
- Records creator provider.
- Initializes empty progress, capability, and safety sections.
