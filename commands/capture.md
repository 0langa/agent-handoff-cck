---
name: capture
description: Update handoff from current work state.
---

# Agent Handoff: capture

Update the active handoff from the current chat/session summary.

## Chat-native behavior

Call the MCP tool `handoff_capture`.

Agent behavior:

1. Summarize what was done, what is in progress, and the next steps.
2. Pass concise lists to `done`, `current`, `next`, and `blockers`.
3. Include important files, decisions, constraints, and open questions.
4. Record commands run and tests run as structured objects.
5. Set `target_provider` if the user wants to hand off to a specific provider.
6. Set `secrets_touched=true` and list `sensitive_sources` if applicable.
7. Record destructive actions and anything needing user approval.

If no active handoff exists, provide `title` (and optionally `objective`) to auto-initialize.

## CLI fallback

If MCP is unavailable, run from the repository root:

```text
agent-handoff capture --provider codex --done "step A" --next "step B"
```

## Safety

- Do not capture `.env` contents or raw secret values.
- Redact token-like strings in command outputs.
