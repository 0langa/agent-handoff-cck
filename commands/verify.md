---
name: verify
description: Verify handoff quality before switching providers.
---

# Agent Handoff: verify

Verify handoff quality before switching providers by running the CLI from the repository root.

Use the arguments supplied after the slash command as CLI arguments:

```text
agent-handoff verify $ARGUMENTS
```

If `agent-handoff` is not on PATH and this is the plugin source checkout, use:

```text
uv run agent-handoff verify $ARGUMENTS
```

Report failures and warnings directly. Do not mark a handoff ready if verification fails.

- Schema valid
- Objective and status present
- Next actions present unless complete
- Tests run or explicitly skipped
- Changed files captured
- Required capabilities have fallbacks
- Secrets touched flag accurate
- Destructive actions recorded
- Git status staleness warning

## Output

- `PASS` or list of failures/warnings.
