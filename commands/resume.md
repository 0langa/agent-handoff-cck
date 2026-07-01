# /handoff resume

Continue from latest handoff.

## Usage

```text
agent-handoff resume --provider claude-code
```

## Behavior

- Reads `.handoff/active.json`.
- Validates schema.
- Checks current provider against required capabilities.
- Prints continuation summary from `.handoff/active.md`.
- Stops if a required capability is blocked and no fallback exists.
