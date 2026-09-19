---
name: agent-handoff
description: Use when the user wants to hand off, checkpoint, resume, verify, export, transfer, or continue a coding session/task between Codex, Claude Code, Kimi Code, or create a new session with context loaded and waiting.
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
- "new session loaded and waiting"
- "pause here and prepare a new task"
- "switch agents"

Trigger words: `kimi`, `kimi-code`, `kimi code`, `claude`, `claude-code`, `claude code`, `codex`, `new codex chat`, `new chat`, `handoff`, `checkpoint`, `resume`, `verify`, `export`, `transfer`, `continue`.

## Core rule

Prefer the Agent Handoff **MCP tools**. Do not tell the user to run CLI commands unless MCP is unavailable or the user explicitly asks for the terminal fallback.

Always pass `repo_root` explicitly to every MCP tool call. Use the active workspace/repository root, not the plugin installation directory. This is required because some hosts launch plugin MCP servers from a managed plugin directory.

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

### New session with context loaded and waiting

When the user explicitly requests a new session, chat or task as part of the
handoff, use the host's task-creation tools when available. The desired result is
**a new task that has read the handoff and is paused**, not merely an export file.
Default to loading and waiting; continue work there only when the user explicitly
requests immediate continuation. A checkpoint-only or export-only request does
not authorize creating a task.

Read [the new-session workflow](references/new-session.md) and follow it:

1. Capture, strictly verify, and export the current handoff with explicit `repo_root`.
2. Discover the host's task tools. In Codex Desktop these are `list_projects`,
   `create_thread` and `wait_threads`; they belong to the host, not this MCP server.
3. Create one task with the verified checkpoint, exact source location and explicit
   load-and-wait instructions. Preserve the user's pause and scope boundaries.
4. Wait for that task's completed acknowledgement. A returned task ID, queued
   creation, commentary or an idle task alone does not prove context was loaded.
5. Save the destination and observed result under `.handoff/sessions/`; return the
   task link and a brief status. Never create a duplicate after an uncertain result.

If the host cannot create or observe tasks, use the export fallback and name the
missing capability. Do not claim a new session exists or is ready without evidence.

### Hand off to another provider

1. Summarize the current session in your own words.
2. Call `handoff_capture` with `repo_root` and `target_provider` set to the inferred target.
3. Call `handoff_verify` with `repo_root` (use `strict=true` if switching providers).
4. Call `handoff_export` with `repo_root` and the same `target_provider`.
5. If the user requested a new session, follow the new-session workflow above when
   the host supports that target. Otherwise return the export path and the manual
   next step. Do not invent cross-app task creation capabilities.

### Resume the latest handoff

1. Call `handoff_resume` with `repo_root`.
2. Read the returned continuation summary and `active.md`.
3. If this is new-session setup with load-and-wait instructions, acknowledge the
   loaded handoff and stop. Calling `handoff_resume` reads context; it does not
   override a pause. Otherwise continue from the next steps, respecting capability
   warnings, safety notes and the user's current instruction.

### Check status

1. Call `handoff_status` with `repo_root`.
2. Report title, status, next-step count, and blocker count.

### Close

1. Call `handoff_close` with `repo_root` when the task is finished.
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
