# /handoff init

Create a new handoff record.

## Usage

```text
agent-handoff init --title "Fix auth bug" --objective "Resolve token expiry check" --provider codex
```

## Behavior

- Creates `.handoff/active.json` and `.handoff/active.md`.
- Records creator provider.
- Initializes empty progress, capability, and safety sections.
