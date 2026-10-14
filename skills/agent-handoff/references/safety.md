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

Everything written to `.handoff/` is redacted before storage, whether it comes from the MCP tools or the CLI. Redaction replaces:

- values after secret key names, as in `api_key: ...`, `"client_secret": "..."`, `GITHUB_TOKEN=...` or `Authorization: Bearer ...`. Names such as `tokenizer`, `max_tokens` or `secretary` are left alone.
- values of secret CLI flags, such as `--token`, `--password`, `--api-key` and `--secret`.
- passwords in URLs: `https://user:[REDACTED]@host`.
- well-known token formats on their own: GitHub, OpenAI, Anthropic, AWS access key IDs, Slack, Google, GitLab, npm and JWTs.

`handoff_capture` rejects free-text items that contain such values. Redaction is pattern-based, so summarize secrets instead of pasting them: a password in plain prose without a key or flag is not detected.
