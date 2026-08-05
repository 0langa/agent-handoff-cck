# Agent Handoff — Status & Roadmap
_Portfolio audit: 2026-07-11_

## What this is

A chat-native cross-agent handoff plugin that lets Codex, Claude Code, and Kimi Code continue
each other's work: an MCP server exposes seven tools (`handoff_init`, `handoff_capture`,
`handoff_status`, `handoff_resume`, `handoff_verify`, `handoff_export`, `handoff_close`) that
persist provider-neutral task state under `.handoff/` and render provider-specific continuation
prompts. Stack: Python 3.10+ (`pydantic`, `click`, `jinja2`, `mcp`), a JSON Schema contract
(`schemas/handoff.schema.json`), Jinja2 export templates per provider, a Click CLI fallback,
and pytest.

## Current state

The 0.2.x milestone defined in `DEVELOPMENT_PLAN.md` is essentially implemented.

What works:

- `src/agent_handoff/` carries the full pipeline: `mcp_server.py` (674 lines, all seven tools),
  `cli.py` (414 lines), `schema.py`, `store.py` (history snapshots), `verify.py`, `export.py`
  with `templates/export-*.md.j2`, `privacy.py` (secret redaction), `capabilities.py`
  (fallback taxonomy), and `git_context.py`.
- The chat surface is complete: `skills/agent-handoff/SKILL.md`, eight command prompts under
  `commands/`, and two agents (`agents/handoff-summarizer.md`, `agents/handoff-verifier.md`).
- Test coverage is the broadest of the four portfolio projects: eleven files under `tests/`
  covering the MCP tools, CLI, schema, store, verify, render, privacy, provider aliases,
  provider manifests, and skill-routing text.
- The plugin provably works in practice: it is loaded in the live environment, and the tracked
  `.handoff/` records in the sibling `customization-control` repo were produced by it.
- Recent commits show real hardening: an stdio pipe-inheritance fix for git subprocesses, input
  hardening for capture, an explicit repo-root requirement, and a pinned `uv --project` root in
  `.mcp.json` (commit `dbfb3f7`).

Gaps and loose ends:

- **Release metadata is aligned at 0.2.2**: `pyproject.toml`, the runtime package, README, and
  all three provider manifests agree; tags `v0.2.1` and `v0.2.2` exist. The manifest test now
  guards this agreement.
- The marketplace rollout in the plan's Done Definition (updating the
  `0langas-plugin-marketplace` submodule and metadata to 0.2.x) is not verifiable from this
  repo and is presumably outstanding.
- The CI workflow defines compile, Ruff, and pytest gates on Windows and Linux. The README documents Kimi's
  `/agent-handoff:*` namespace separately from Claude's `/handoff:*` commands.

## Definition of "finished"

The version-and-tag baseline is met at `v0.2.2`, and CI defines the local compile, lint, and pytest
gates. The marketplace submodule and metadata must match the tagged version and installs must be
refreshed on all three providers. Every acceptance and smoke
check in `DEVELOPMENT_PLAN.md` — chat-native prompts such as "handoff this session to kimi now"
producing capture → verify → export with `.handoff/exports/kimi-code.md` — has been executed at
least once per provider, and the README reflects the final version and per-provider command
namespaces.

## Roadmap

### Phase 1 — Now (next 1-2 weeks)

- For the next release, tag it and complete the marketplace rollout steps from
  `DEVELOPMENT_PLAN.md` (submodule bump, metadata update, provider install refresh).
- Run the chat-native smoke prompts from the plan in each provider and record the results,
  replacing any assumed-but-unverified provider behavior.

### Phase 2 — Next (2-6 weeks)

- Keep the provider-manifest and runtime-version tests alongside future version bumps.
- Add a short troubleshooting note for the `uv --project` MCP launch
  path fixed in commit `dbfb3f7`.
- Round out edge-case tests: concurrent or stale `.handoff/` state, `handoff_capture` merge
  behavior across repeated calls, and `handoff_resume` capability-blocked paths.

### Phase 3 — Later (optional/stretch)

- Attachment hardening: `.handoff/attachments/` diffs and logs are described in the README but
  deserve size limits and redaction tests via `privacy.py`.
- A `handoff_list` or history-browsing tool over `.handoff/history/` snapshots.
- Optional integration with Usage Pulse to stamp session statistics into captures.

## Effort to "finished"

**S (a few days of part-time work).** The feature set, tests, release metadata, and CI are in
place; what remains is marketplace/metadata sync for the next release and one round of
per-provider smoke validation.
