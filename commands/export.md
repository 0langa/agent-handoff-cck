---
name: export
description: Generate continuation prompt for target provider.
---

# /handoff export

Generate continuation prompt for target provider.

## Usage

```text
agent-handoff export codex
agent-handoff export claude-code
agent-handoff export kimi-code
agent-handoff export generic
```

## Output

- `.handoff/exports/codex.md`
- `.handoff/exports/claude-code.md`
- `.handoff/exports/kimi-code.md`
- `.handoff/exports/unknown.md` (for generic)

## Content

Each export includes role-specific instructions, objective, status, next actions, capability warnings, safety constraints, file paths, and tests run.
