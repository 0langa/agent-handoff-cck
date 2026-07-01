---
name: verify
description: Verify handoff quality before switching providers.
---

# /handoff verify

Verify handoff quality before switching providers.

## Usage

```text
agent-handoff verify --provider claude-code --strict
```

## Checks

- Schema valid
- Objective and status present
- Next actions present unless complete
- Tests run or explicitly skipped
- Changed files captured
- Required capabilities have fallbacks
- Secrets touched flag accurate
- Destructive actions recorded
- Git status staleness warning

## Output

- `PASS` or list of failures/warnings.
