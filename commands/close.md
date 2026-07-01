# /handoff close

Mark task complete and archive.

## Usage

```text
agent-handoff close --provider codex
```

## Behavior

- Sets status to `complete`.
- Adds final history snapshot.
- Removes `.handoff/active.json` and `.handoff/active.md`.
- Optionally writes summary to RECALL if configured.
