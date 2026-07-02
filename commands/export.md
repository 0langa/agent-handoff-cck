---
name: export
description: Generate continuation prompt for target provider.
---

# Agent Handoff: export

Generate a continuation prompt for a target provider.

## Chat-native behavior

Call the MCP tool `handoff_export` with `repo_root` and `target_provider`.

Always pass `repo_root` explicitly. Use the active workspace/repository root, not the plugin installation directory.

Supported targets:

- `codex`
- `claude-code`
- `kimi-code`
- `generic` / `unknown`

Agent behavior:

1. Confirm the target provider if not supplied.
2. Call `handoff_export`.
3. Show the export path and a short preview.
4. Tell the user how to use the export in the target agent.

## CLI fallback

If MCP is unavailable, run from the repository root:

```text
agent-handoff export claude-code
```
