# Create a session, load context, then wait

This is a cooperative handoff by the current agent. The plugin supplies the
workflow and checkpoint; the host supplies task creation and observation. This
does not recover an unavailable agent or provide a universal cross-app launcher.

## Request and checkpoint

- Require an explicit request for a new session/chat/task. Do not spawn for a bare
  capture, checkpoint, export, status, or resume request. Never spawn recursively
  when the destination is only loading a handoff.
- Default to **load and wait**. If the user explicitly requests immediate work in
  the destination, record that separately. A pause takes precedence over older
  autonomous next steps until the user resumes.
- Call `handoff_status` first when an active record may exist. `handoff_capture`
  merges lists; it does not clear stale blockers or replace the title. If the record
  belongs to an obsolete task, preserve its JSON and Markdown byte-for-byte in
  history before `handoff_init(force=true)`. Never mark unfinished work complete
  just to replace the record. Keep valid current context when it is the same task.
- Capture the actual current state, boundaries, exact important paths, tests and
  next steps. Strictly verify for the target provider, then export. Stop preparation
  if verification fails; resolve the concrete missing evidence first.
- Preserve a unique copy of the verified export under `.handoff/sessions/` before
  creating the task. Use a new locally generated request ID for filenames and keep
  the original `handoff_id` and `updated_at`. Never overwrite an existing copy.
  The mutable `exports/codex.md` alone is not a stable checkpoint for an async task.
- Record the source repo root and export's SHA-256. Use absolute paths in the
  bootstrap. Never include credentials, cookies or raw private connector output.

## Host capability and destination

Discover the actual callable tools and read their schemas. Do not treat these tool
names as portable APIs inside the Python MCP server.

For Codex Desktop:

1. Use `list_projects` and match the exact source project path and intended host.
   Follow the host's project/environment rules: Git projects default to a worktree;
   non-Git projects use local. Follow an explicit request to use the saved project
   directly. Do not guess a project ID, branch, model or host.
2. A worktree may omit uncommitted source files and ignored handoff artifacts.
   Include the frozen handoff text in the bootstrap when the destination cannot
   read its absolute path. Record source and destination separately. Do not silently
   copy working-tree changes or claim the destination has the same checkout.
   A missing source artifact must be reported before later implementation resumes.
3. Use `create_thread` once. Keep model/reasoning defaults unless the user specifies
   them. Pass a cohesive user-visible bootstrap, not only a filename or "continue".
4. Preserve the returned `threadId` and `hostId`. A `clientThreadId` means queued
   creation; it is not a usable `threadId`. Resolve queued creation through the
   host's supported observation tools before waiting on the actual task.
5. Use `wait_threads` with the returned identity and subsequent cursor. Use bounded
   waits of at most 60 seconds; avoid unchanged busy polling. Only a completed final
   acknowledgement that identifies this handoff and its paused state establishes
   **loaded and paused**. An idle snapshot alone is insufficient.

If no project matches, do not silently attach to another project. Use the host's
supported projectless context when appropriate, with the explicit source path and
its limitations, or report that destination selection is needed.

Other hosts may expose equivalent capabilities. Use them only when their actual
tools support the requested destination. If creation is unavailable, return the
verified export and say **export ready; no task created**. If creation succeeds but
observation is unavailable, say **task created; context loading unconfirmed**.
Do not launch an external CLI or GUI as a substitute unless the user requests it.

## Destination bootstrap

Expand the placeholders from verified local state. Include the request ID in the
prompt so an uncertain creation can be reconciled without spawning another task.

```text
Load Agent Handoff <handoff_id>, request <request_id>, for <absolute source repo>.
Checkpoint: <absolute immutable export path>, SHA-256 <export hash>.
Your task is to read and acknowledge this context, then remain paused until the
user asks to continue. Do not create another task or advance implementation.

Read applicable workspace instructions. Use Agent Handoff handoff_resume with
repo_root=<absolute source repo> if available, then read the pinned export and
referenced current status documents. If active.json now identifies another capture,
use the pinned export for this request and report the mismatch; do not mix states.
Use available project-memory tools according to their instructions. If the export
was embedded instead, use that captured text and report inaccessible local artifacts.

Preserve these user boundaries: <scope, pause, preferences, actual human needs>.
Do not launch browsers, run builds, change product files, submit provider work or
resume old next steps during setup. Do not repeat settled permission/sign-in requests.
Report missing context honestly. If context is loaded, end your turn with:
"Handoff <handoff_id> loaded. Paused until you resume."
```

An explicit user request to continue immediately changes the execution instruction,
not the accuracy requirements. Do not simultaneously tell that task to stay paused
and to begin work. Do not mutate the source handoff to erase a user pause on your own.

## Receipt, failures and delivery

Write a receipt beside the frozen export under `.handoff/sessions/`. Use a locally
generated filename, never an unchecked host-returned ID as a path. Include:

- Request ID, handoff ID, capture timestamp, source root, export path and hash.
- Requested mode (`load-and-wait` or explicit `continue`) and target provider.
- Actual destination `threadId`/`hostId`, or a separately labelled queued client ID.
- Observed state: `exported`, `created`, `loaded-and-paused`, `continuing`,
  `failed`, or `unconfirmed`; store only states supported by tool evidence.
- Relevant completion turn/cursor and the brief acknowledgement or failure reason.

Save the creation result before waiting. After a timeout, disconnect, interrupted
source turn or ambiguous create response, inspect that receipt and the host's
existing tasks for this request ID. Never blindly retry creation. If the outcome
cannot be reconciled, report it as unconfirmed and keep the export usable.

Do not claim paused readiness while a destination is still running or says it needs
context. If a load-and-wait task starts implementation unexpectedly, use the host's
supported interrupt mechanism and report the deviation; do not send more work.
Do not kill unrelated processes or archive/delete the source task automatically.

Return the actual task link using the host's required created-task directive when
available, plus one short outcome. Keep the export link as a fallback. A receipt of
context loading is not proof that future builds or provider features will work.
