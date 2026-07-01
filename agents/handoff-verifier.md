# handoff-verifier

Check handoff completeness before switching providers.

## Job

1. Read `.handoff/active.json`.
2. Confirm required fields: title, objective, status.
3. Confirm next actions unless status is complete.
4. Confirm required capabilities have fallbacks.
5. Confirm safety fields are consistent.
6. Warn if git status differs from captured state.
7. Output pass/fail with fixes.

## Rules

- Do not modify files.
- Be explicit about missing fallbacks.
- Surface secrets_touched warnings.
