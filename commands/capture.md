---
name: capture
description: Update handoff from current work state.
---

# /handoff capture

Update handoff from current work state.

## Usage

```text
agent-handoff capture --provider codex --done "reproduced bug" --next "patch middleware" --command "pytest|run tests|success"
```

## Behavior

- Captures git status and changed files.
- Records commands and tests run.
- Adds progress, decisions, constraints.
- Captures capabilities used.
- Updates `.handoff/active.json`, `.handoff/active.md`, and adds history snapshot.

## Safety

- Does not capture `.env` or secret values.
- Redacts token-like strings in command outputs.
