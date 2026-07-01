# Agent Continuity / agent-handoff

Capture and resume cross-agent handoffs between Codex, Claude Code, and Kimi Code.

## When to use

- You are switching agents and need the next one to continue without losing context.
- You want to checkpoint current progress, blockers, and next steps.
- You need a provider-neutral artifact any agent can read.

## Core commands

- `agent-handoff init --title "..." --objective "..."` — start a handoff.
- `agent-handoff capture` — update the handoff from current state.
- `agent-handoff status` — quick status.
- `agent-handoff resume` — read the handoff and continue.
- `agent-handoff verify` — check completeness before switching providers.
- `agent-handoff export codex|claude-code|kimi-code|generic` — generate continuation prompt.
- `agent-handoff close` — mark complete and archive.

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

- `captured-result` — enough data is in the handoff; continue.
- `manual-user-input` — user must paste/export data.
- `switch-provider` — resume in provider that has the capability.
- `local-equivalent` — use shell/MCP/API equivalent.
- `skip-safe` — optional step.
- `blocked` — cannot continue safely.

## Provider-specific notes

- Codex: use `@agent-handoff capture` style commands if supported.
- Claude Code: use `/handoff:*` slash commands.
- Kimi Code: use `/agent-handoff:*` commands.

All providers read and write the same `.handoff/active.json` schema.
