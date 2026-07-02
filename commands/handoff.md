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

1. Infer `target_provider` from `$ARGUMENTS`:
   - `kimi`, `kimi-code`, `kimi code` → `kimi-code`
   - `claude`, `claude-code`, `claude code` → `claude-code`
   - `codex`, `openai codex` → `codex`
   - `new chat`, `same`, `same-provider` → current provider
2. Summarize the current session.
3. Call the MCP tool `handoff_capture` with `target_provider`.
4. Call the MCP tool `handoff_verify` with `strict=true`.
5. Call the MCP tool `handoff_export` with the same `target_provider`.
6. Return the export path and a short next instruction.

If the target cannot be inferred, ask the user which provider to use.
