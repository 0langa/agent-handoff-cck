---
name: verify
description: Verify handoff quality before switching providers.
---

# Agent Handoff: verify

Verify handoff quality before switching providers or chats.

## Chat-native behavior

Call the MCP tool `handoff_verify`.

Agent behavior:

1. Pass the current provider if known.
2. Use `strict=true` when the user is about to switch providers.
3. Report PASS/FAIL, warnings, errors, and concrete fixes.
4. Do not claim the handoff is ready if verification fails.

## CLI fallback

If MCP is unavailable, run from the repository root:

```text
agent-handoff verify --provider claude-code --strict
```
