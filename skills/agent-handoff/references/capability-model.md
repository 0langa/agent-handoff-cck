# Capability Model

## Problem

Providers have different tools, MCP servers, connectors, and apps. A handoff must not assume the next provider has the same capabilities.

## Recording a capability

Each capability entry records:

- `provider` — which provider used it.
- `type` — plugin, mcp, app, shell, filesystem, browser, manual.
- `id` — stable identifier, e.g. `gmail@openai-curated-remote`.
- `purpose` — what it was used for.
- `outputs_captured` — whether results were safely captured in the handoff.
- `required_to_continue` — whether the next agent needs it.
- `fallback` — what to do if unavailable.

## Fallback types

| Type | Meaning |
|------|---------|
| `captured-result` | Enough captured in handoff; no rerun needed. |
| `manual-user-input` | User must provide data. |
| `switch-provider` | Resume in provider that has the tool. |
| `local-equivalent` | Use shell/MCP/API equivalent. |
| `skip-safe` | Optional step. |
| `blocked` | Cannot continue safely without it. |

## Example: Codex Gmail connector

```json
{
  "provider": "codex",
  "type": "plugin",
  "id": "gmail@openai-curated-remote",
  "purpose": "searched inbox for client email",
  "outputs_captured": true,
  "required_to_continue": false,
  "fallback": {
    "type": "captured-result",
    "details": "Claude/Kimi can continue from captured summary unless a fresh inbox check is needed."
  }
}
```

If a fresh inbox check is required next:

```json
{
  "required_to_continue": true,
  "fallback": {
    "type": "switch-provider",
    "details": "Switch back to Codex or add a mail MCP server."
  }
}
```
