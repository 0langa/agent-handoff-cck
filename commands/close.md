---
name: close
description: Mark task complete and archive.
---

# Agent Handoff: close

Mark the task complete and archive the handoff.

## Chat-native behavior

Call the MCP tool `handoff_close`.

Agent behavior:

1. Only close when the task is finished or the user explicitly asks.
2. Optionally pass a final `summary`.
3. Report the archive path under `.handoff/history/`.

## CLI fallback

If MCP is unavailable, run from the repository root:

```text
agent-handoff close --provider codex
```
