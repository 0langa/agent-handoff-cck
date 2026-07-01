# handoff-summarizer

Compress current work state into a durable handoff.

## Job

1. Inspect git status and changed files.
2. Summarize done, current, and next steps.
3. Record decisions, constraints, open questions.
4. List capabilities used and required next.
5. Note safety issues and sensitive sources.
6. Write concise resume summary and next prompt.
7. Save to `.handoff/active.json` and `.handoff/active.md`.

## Rules

- Do not capture raw secrets, `.env`, tokens, or private messages.
- Prefer summaries over raw external data.
- Use capability fallbacks for provider-bound tools.
