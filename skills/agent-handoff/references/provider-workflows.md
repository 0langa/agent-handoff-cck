# Provider Workflows

## Codex

Manifest: `.codex-plugin/plugin.json`

Verified workflow:

```text
agent-handoff capture --provider codex
agent-handoff resume --provider codex
agent-handoff export claude-code
```

Implementation notes:

- Use Codex filesystem/git tools when available.
- Record Codex-specific connectors (Gmail, GitHub).
- Do not assume Claude/Kimi have Codex connectors.
- Plugin-native command installation depends on the Codex marketplace/client install path.

## Claude Code

Manifest: `.claude-plugin/plugin.json`

Verified workflow:

```text
agent-handoff init --provider claude-code
agent-handoff capture --provider claude-code
agent-handoff resume --provider claude-code
agent-handoff verify --provider claude-code
agent-handoff export codex
```

Implementation notes:

- Prefer shell/git inspection.
- Avoid auto-running destructive commands.
- Claude Code can structurally validate `.claude-plugin/plugin.json`.
- Slash commands may be available when the client discovers the `commands/` directory.

## Kimi Code

Manifest: `kimi.plugin.json`

Verified workflow:

```text
agent-handoff init --provider kimi-code
agent-handoff capture --provider kimi-code
agent-handoff resume --provider kimi-code
agent-handoff verify --provider kimi-code
agent-handoff export claude-code
```

Implementation notes:

- Kimi Code CLI uses the in-session `/plugins install <path-or-url>` workflow, not a shell `kimi plugin install` subcommand.
- `kimi.plugin.json` declares `skills`, `commands`, and `sessionStart.skill`; after plugin installation and `/reload`, commands should be namespaced as `/agent-handoff:<command>`.
- Keep command prompts provider-neutral.
- Detect Kimi-only limitations and request fallback if needed.

## Cross-provider rule

Every provider reads/writes the same `.handoff/active.json` schema. Provider-specific export prompts adapt the same data to each client's conventions.
