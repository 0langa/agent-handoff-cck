---
name: init
description: Create a new handoff record.
---

# Agent Handoff: init

Create a new handoff record.

## Chat-native behavior

Call the MCP tool `handoff_init` with:

- `title` (required)
- `objective` (optional)
- `target_provider` (optional: codex, claude-code, kimi-code, generic)
- `provider` (optional, defaults to auto-detected current provider)
- `repo_root` (optional, defaults to current working directory)

Do not overwrite an existing active handoff unless `force=true`.

## CLI fallback

If MCP is unavailable, run from the repository root:

```text
agent-handoff init --title "..." --objective "..." --provider codex
```

## Output

Creates `.handoff/active.json` and `.handoff/active.md`.
