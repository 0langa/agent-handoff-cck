---
name: agent-handoff
description: Use when the user wants to hand off, checkpoint, resume, verify, export, transfer, or continue a coding session/task between Codex, Claude Code, Kimi Code, or a new chat.
---

# Agent Handoff / agent-handoff

Capture and resume cross-agent handoffs between Codex, Claude Code, and Kimi Code.

## When to activate

Activate this skill when the user says anything like:

- "hand off this task to Kimi"
- "handoff this session to claude code"
- "continue this in Codex"
- "make a codex handoff for a new chat"
- "checkpoint this task before I switch agents"
- "resume the latest handoff"
- "verify this handoff before switching"
- "transfer this to another agent"
- "new chat with context"
- "switch agents"

Trigger words: `kimi`, `kimi-code`, `kimi code`, `claude`, `claude-code`, `claude code`, `codex`, `new codex chat`, `new chat`, `handoff`, `checkpoint`, `resume`, `verify`, `export`, `transfer`, `continue`.

## Core rule

Prefer the Agent Handoff **MCP tools**. Do not tell the user to run CLI commands unless MCP is unavailable or the user explicitly asks for the terminal fallback.

## Available MCP tools

- `handoff_init` — create `.handoff/active.json` and `.handoff/active.md`.
- `handoff_capture` — update the active handoff from the current session summary.
- `handoff_status` — quick state check.
- `handoff_resume` — read the active handoff and continue.
- `handoff_verify` — check completeness before switching providers.
- `handoff_export` — generate a continuation prompt for a target provider.
- `handoff_close` — mark complete and archive.

Tool names may be namespaced by the host, e.g. `mcp__agent-handoff__handoff_capture`.

## Common flows

### Hand off to another provider

1. Summarize the current session in your own words.
2. Call `handoff_capture` with `target_provider` set to the inferred target.
3. Call `handoff_verify` (use `strict=true` if switching providers).
4. Call `handoff_export` with the same `target_provider`.
5. Tell the user the export path and the next step (open the target agent and paste/run the export).

### Resume the latest handoff

1. Call `handoff_resume`.
2. Read the returned continuation summary and `active.md`.
3. Continue from the next steps, respecting capability warnings and safety notes.

### Check status

1. Call `handoff_status`.
2. Report title, status, next-step count, and blocker count.

### Close

1. Call `handoff_close` when the task is finished.
2. Report the archive path.

## Provider aliases

Normalize these aliases before passing them to tools:

| User input | Normalized |
| --- | --- |
| `kimi`, `kimi-code`, `kimi code` | `kimi-code` |
| `claude`, `claude-code`, `claude code` | `claude-code` |
| `codex`, `openai codex` | `codex` |
| `same`, `same-provider`, `new chat` | current provider |
| `generic` | `unknown` |

For "new chat" without a provider, use the current provider as the target.

## Files

- `.handoff/active.json` — canonical machine-readable handoff.
- `.handoff/active.md` — human-readable fallback.
- `.handoff/history/` — immutable snapshots.
- `.handoff/exports/` — provider-specific continuation prompts.

## Safety rules

- Never capture `.env` contents, tokens, keys, passwords, or raw email bodies.
- Summarize external connector results instead of copying raw data.
- Mark secrets touched and list sensitive sources when applicable.
- Use capability fallbacks when the next provider lacks a tool.

## Capability fallbacks

When a capability is provider-bound, record a fallback:

| Fallback type | Meaning |
| --- | --- |
| `captured-result` | Enough data is in the handoff; no rerun needed. |
| `manual-user-input` | User must paste/export data. |
| `switch-provider` | Resume in provider that has the tool. |
| `local-equivalent` | Use shell/MCP/API equivalent. |
| `skip-safe` | Optional step. |
| `blocked` | Cannot continue safely. |
