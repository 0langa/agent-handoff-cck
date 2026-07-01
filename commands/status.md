---
name: status
description: Show current handoff status.
---

# Agent Handoff: status

Show current handoff status by running the CLI from the repository root.

Use the arguments supplied after the slash command as CLI arguments:

```text
agent-handoff status $ARGUMENTS
```

If `agent-handoff` is not on PATH and this is the plugin source checkout, use:

```text
uv run agent-handoff status $ARGUMENTS
```

Report the CLI output directly and summarize only if the user asked for a summary.

- Title
- Status
- Created/updated by
- Updated at
- Number of next steps and blockers
