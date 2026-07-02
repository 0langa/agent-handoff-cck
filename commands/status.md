---
name: status
description: Show current handoff status.
---

# Agent Handoff: status

Show current handoff status.

## Chat-native behavior

Call the MCP tool `handoff_status`.

Report:

- Whether an active handoff exists.
- Title and status.
- Created/last-updated provider.
- Updated timestamp.
- Number of next steps and blockers.
- Paths to `.handoff/active.json` and `.handoff/active.md`.

## CLI fallback

If MCP is unavailable, run from the repository root:

```text
agent-handoff status
```
