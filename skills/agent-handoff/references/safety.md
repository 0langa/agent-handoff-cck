# Safety Model

## Default deny

Do not capture by default:

- `.env` files and environment variable dumps.
- API keys, tokens, passwords, credentials.
- Raw email bodies or private messages.
- Full logs that may contain headers or tokens.
- Browser session data.
- MCP configs with secrets.

## Sensitive sources

List sources that were involved, not raw content:

- `gmail`
- `webde`
- `email-body`
- `browser-session`
- `credential-store`
- `api-key`
- `auth-header`

## Secrets touched flag

Set `safety.secrets_touched = true` when any secret material was read, edited, or generated. Always list the sensitive source.

## Destructive actions

Record any destructive action and mark whether it needs user approval:

- deleting files or data
- dropping tables
- force-pushing code
- modifying production resources

## Privacy notes

Add short notes explaining what was avoided and why:

> "Used Codex Gmail connector. Captured relevant facts only. Fresh inbox check requires switching back to Codex or adding an equivalent mail connector."

## Redaction

Command outputs are scanned for token-like values and redacted before storage.
