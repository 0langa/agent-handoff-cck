---
name: resume
description: Continue from latest handoff.
---

# Agent Handoff: resume

Continue from the latest handoff.

## Chat-native behavior

Call the MCP tool `handoff_resume` with `repo_root`.

Always pass `repo_root` explicitly. Use the active workspace/repository root, not the plugin installation directory.

Agent behavior:

1. Load and validate `.handoff/active.json`.
2. Read the returned continuation summary and `.handoff/active.md`.
3. Respect capability warnings; if a required capability is blocked, stop and ask the user.
4. Continue from the recorded next steps.

## CLI fallback

If MCP is unavailable, run from the repository root:

```text
agent-handoff resume --provider claude-code
```
