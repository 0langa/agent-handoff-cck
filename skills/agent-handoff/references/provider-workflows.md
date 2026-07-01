# Provider Workflows

## Codex

Manifest: `.codex-plugin/plugin.json`

User-facing commands:

```text
@agent-handoff capture current task
@agent-handoff resume latest handoff
@agent-handoff export claude-code
```

Implementation notes:

- Use Codex filesystem/git tools when available.
- Record Codex-specific connectors (Gmail, GitHub).
- Do not assume Claude/Kimi have Codex connectors.

## Claude Code

Manifest: `.claude-plugin/plugin.json`

Slash commands:

```text
/handoff:init
/handoff:capture
/handoff:resume
/handoff:status
/handoff:verify
/handoff:export
/handoff:close
```

Implementation notes:

- Prefer shell/git inspection.
- Avoid auto-running destructive commands.
- Use agents for verification and summarization later.

## Kimi Code

Manifest: `kimi.plugin.json`

Commands:

```text
/agent-handoff:init
/agent-handoff:capture
/agent-handoff:resume
/agent-handoff:status
/agent-handoff:verify
/agent-handoff:export
/agent-handoff:close
```

Implementation notes:

- Use Kimi plugin command namespace.
- Keep command prompts provider-neutral.
- Detect Kimi-only limitations and request fallback if needed.

## Cross-provider rule

Every provider reads/writes the same `.handoff/active.json` schema. Provider-specific export prompts adapt the same data to each client's conventions.
