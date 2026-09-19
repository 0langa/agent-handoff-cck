---
name: handoff
description: One-shot handoff to a target provider or new chat.
---

# Agent Handoff: handoff

One-shot handoff to a target provider or new chat.

## Usage

```text
/handoff kimi
/handoff claude
/handoff codex
/handoff new chat
```

`$ARGUMENTS` is the target provider alias.

## Chat-native behavior

Always pass `repo_root` explicitly to every MCP tool call. Use the active workspace/repository root, not the plugin installation directory.

For an explicit new-session request, read
`skills/agent-handoff/references/new-session.md` before capture, including its stale
record check. Reuse the capture/verification/export from this invocation when entering
its creation steps; do not perform those steps twice.

1. Infer `target_provider` from `$ARGUMENTS`:
   - `kimi`, `kimi-code`, `kimi code` → `kimi-code`
   - `claude`, `claude-code`, `claude code` → `claude-code`
   - `codex`, `openai codex` → `codex`
   - `new chat`, `same`, `same-provider` → current provider
2. Summarize the current session.
3. Call the MCP tool `handoff_capture` with `repo_root` and `target_provider`.
4. Call the MCP tool `handoff_verify` with `repo_root` and `strict=true`.
5. Call the MCP tool `handoff_export` with `repo_root` and the same `target_provider`.
6. For an explicit new chat/session/task request, follow
   `skills/agent-handoff/references/new-session.md`: use available host task tools
   to create one task, load the verified handoff and confirm it is paused. Default
   to loading and waiting unless immediate continuation was explicitly requested.
   Save the destination receipt and return the host's task link.
7. If host task creation is unavailable, return the export path and explain the
   manual next step. Never claim context is loaded from a task ID alone, and never
   create a duplicate after an uncertain response.

If the target cannot be inferred, ask the user which provider to use.
