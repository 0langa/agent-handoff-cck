"""MCP server for chat-native agent handoff.

Exposes seven tools that reuse the internal handoff logic:

- handoff_init
- handoff_capture
- handoff_status
- handoff_resume
- handoff_verify
- handoff_export
- handoff_close

Run as a stdio MCP server:

    python -m agent_handoff.mcp_server
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from .capabilities import check_missing_capabilities
from .export import export_to
from .git_context import changed_files, git_status, is_git_repo
from .privacy import redact_tokens, safe_changed_files, safe_git_status, scan_for_secrets
from .render import render_active
from .schema import (
    CapabilityEntry,
    CapabilityType,
    CommandRecord,
    CommandResult,
    FallbackType,
    HandoffSchema,
    Provider,
    TaskStatus,
    TestRecord,
    TestResult,
    detect_provider,
    normalize_provider,
    parse_provider,
)
from .store import close as close_handoff
from .store import exists, get_handoff_dir, load, save, snapshot, write_active_md
from .verify import verify

mcp = FastMCP("agent-handoff", instructions=(
    "Agent Handoff MCP server. Use these tools to capture, verify, export, "
    "resume, and close cross-agent handoffs between Codex, Claude Code, and Kimi Code."
))


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class CommandInput(BaseModel):
    command: str
    purpose: str | None = None
    result: str | None = "unknown"
    notes: str | None = None


class TestInput(BaseModel):
    command: str
    result: str | None = "unknown"
    summary: str | None = None


class CapabilityInput(BaseModel):
    provider: str | None = None
    type: str | None = None
    id: str
    purpose: str | None = None
    outputs_captured: bool | None = False
    required_to_continue: bool | None = False
    fallback_type: str | None = None
    fallback_details: str | None = None


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _repo_path(repo_root: str | None) -> Path:
    return Path(repo_root).resolve() if repo_root else Path.cwd()


def _ok(data: dict[str, Any], markdown: str) -> CallToolResult:
    return CallToolResult(content=[
        TextContent(type="text", text=json.dumps({"ok": True, "data": data}, indent=2)),
        TextContent(type="text", text=markdown),
    ])


def _err(code: str, message: str, markdown: str | None = None) -> CallToolResult:
    payload = {"ok": False, "error": {"code": code, "message": message}}
    return CallToolResult(content=[
        TextContent(type="text", text=json.dumps(payload, indent=2)),
        TextContent(type="text", text=markdown or message),
    ], isError=True)


def _redact(value: str) -> str:
    return redact_tokens(value)


def _normalize_provider(
    value: str | None,
    current: str | Provider | None = None,
) -> Provider:
    if value is None and current is not None:
        return normalize_provider(current)
    if value is None:
        return detect_provider()
    return normalize_provider(value, current=current)


# ---------------------------------------------------------------------------
# Parsing helpers (mirror CLI aliases)
# ---------------------------------------------------------------------------

_COMMAND_RESULT_ALIASES: dict[str, CommandResult] = {
    "ok": CommandResult.SUCCESS,
    "pass": CommandResult.SUCCESS,
    "passed": CommandResult.SUCCESS,
    "success": CommandResult.SUCCESS,
    "succeeded": CommandResult.SUCCESS,
    "green": CommandResult.SUCCESS,
    "fail": CommandResult.FAILED,
    "failed": CommandResult.FAILED,
    "failure": CommandResult.FAILED,
    "error": CommandResult.FAILED,
    "unknown": CommandResult.UNKNOWN,
    "n/a": CommandResult.UNKNOWN,
    "na": CommandResult.UNKNOWN,
    "skipped": CommandResult.UNKNOWN,
}

_TEST_RESULT_ALIASES: dict[str, TestResult] = {
    "ok": TestResult.PASSED,
    "pass": TestResult.PASSED,
    "passed": TestResult.PASSED,
    "success": TestResult.PASSED,
    "succeeded": TestResult.PASSED,
    "green": TestResult.PASSED,
    "fail": TestResult.FAILED,
    "failed": TestResult.FAILED,
    "failure": TestResult.FAILED,
    "error": TestResult.FAILED,
    "skip": TestResult.SKIPPED,
    "skipped": TestResult.SKIPPED,
    "not-run": TestResult.SKIPPED,
    "not_run": TestResult.SKIPPED,
    "unknown": TestResult.UNKNOWN,
    "n/a": TestResult.UNKNOWN,
    "na": TestResult.UNKNOWN,
}


def _parse_command_result(value: str | None) -> CommandResult:
    return _COMMAND_RESULT_ALIASES.get((value or "unknown").strip().lower(), CommandResult.UNKNOWN)


def _parse_test_result(value: str | None) -> TestResult:
    return _TEST_RESULT_ALIASES.get((value or "unknown").strip().lower(), TestResult.UNKNOWN)


def _coerce_model(model: type[BaseModel], item: BaseModel | dict[str, Any]) -> BaseModel:
    if isinstance(item, model):
        return item
    if isinstance(item, dict):
        return model.model_validate(item)
    raise TypeError(f"Expected {model.__name__} or dict, got {type(item).__name__}")


def _to_command_record(item: CommandInput | dict[str, Any]) -> CommandRecord:
    item = _coerce_model(CommandInput, item)
    return CommandRecord(
        command=_redact(item.command),
        purpose=_redact(item.purpose) if item.purpose else None,
        result=_parse_command_result(item.result),
        notes=_redact(item.notes) if item.notes else None,
    )


def _to_test_record(item: TestInput | dict[str, Any]) -> TestRecord:
    item = _coerce_model(TestInput, item)
    return TestRecord(
        command=_redact(item.command),
        result=_parse_test_result(item.result),
        summary=_redact(item.summary) if item.summary else None,
    )


def _to_capability_entry(
    item: CapabilityInput | dict[str, Any],
    default_provider: Provider,
) -> CapabilityEntry:
    item = _coerce_model(CapabilityInput, item)
    cap_provider = parse_provider(item.provider) if item.provider else default_provider
    cap_type = CapabilityType(item.type) if item.type else CapabilityType.MANUAL
    fallback_type = FallbackType(item.fallback_type) if item.fallback_type else FallbackType.BLOCKED
    return CapabilityEntry(
        provider=cap_provider,
        type=cap_type,
        id=item.id,
        purpose=_redact(item.purpose) if item.purpose else "",
        outputs_captured=item.outputs_captured or False,
        required_to_continue=item.required_to_continue or False,
        fallback={
            "type": fallback_type,
            "details": _redact(item.fallback_details) if item.fallback_details else "",
        },
    )


def _merge_list(existing: list[str], incoming: list[str] | None) -> list[str]:
    if not incoming:
        return existing
    combined = list(existing)
    for item in incoming:
        redacted = _redact(item)
        if redacted and redacted not in combined:
            combined.append(redacted)
    return combined


def _scan_and_reject(values: list[str]) -> str | None:
    """Return an error message if a value looks like a raw secret."""
    for value in values:
        if scan_for_secrets(value):
            return (
                "Input contains a secret-looking string. "
                "Summarize sensitive data instead of passing literal tokens/keys."
            )
    return None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def handoff_init(
    title: str,
    objective: str | None = None,
    target_provider: str | None = None,
    repo_root: str | None = None,
    provider: str | None = None,
    force: bool = False,
) -> CallToolResult:
    """Create a new handoff record."""
    root = _repo_path(repo_root)
    handoff_dir = get_handoff_dir(root)

    if exists(handoff_dir) and not force:
        return _err(
            "handoff_exists",
            "Active handoff already exists. Use force=true to overwrite, "
            "or call handoff_capture to update it.",
        )

    try:
        current_provider = _normalize_provider(provider)
    except ValueError as exc:
        return _err("invalid_provider", str(exc))

    handoff = HandoffSchema(
        task={
            "title": _redact(title),
            "objective": _redact(objective) if objective else "",
            "status": TaskStatus.IN_PROGRESS,
        },
        providers={
            "created_by": current_provider,
            "last_updated_by": current_provider,
            "compatible_with": [Provider.CODEX, Provider.CLAUDE_CODE, Provider.KIMI_CODE],
        },
        context={"repo_root": str(root)},
    )

    if target_provider:
        try:
            handoff.resume.recommended_next_provider = _normalize_provider(
                target_provider,
                current_provider,
            )
        except ValueError as exc:
            return _err("invalid_target_provider", str(exc))

    save(handoff, handoff_dir)
    write_active_md(render_active(handoff), handoff_dir)

    return _ok(
        {
            "handoff_id": handoff.handoff_id,
            "paths": {
                "active_json": str(handoff_dir / "active.json"),
                "active_md": str(handoff_dir / "active.md"),
            },
            "provider": current_provider.value,
        },
        f"Created handoff **{handoff.task.title}** at `{handoff_dir / 'active.json'}`.",
    )


@mcp.tool()
def handoff_capture(
    repo_root: str | None = None,
    provider: str | None = None,
    target_provider: str | None = None,
    summary: str | None = None,
    title: str | None = None,
    objective: str | None = None,
    done: list[str] | None = None,
    current: list[str] | None = None,
    next: list[str] | None = None,
    blockers: list[str] | None = None,
    decisions: list[str] | None = None,
    constraints: list[str] | None = None,
    open_questions: list[str] | None = None,
    important_files: list[str] | None = None,
    commands_run: list[CommandInput] | None = None,
    tests_run: list[TestInput] | None = None,
    capabilities_used: list[CapabilityInput] | None = None,
    required_next_capabilities: list[CapabilityInput] | None = None,
    secrets_touched: bool | None = None,
    sensitive_sources: list[str] | None = None,
    destructive_actions: list[str] | None = None,
    needs_user_approval: list[str] | None = None,
    privacy_notes: list[str] | None = None,
    next_prompt: str | None = None,
) -> CallToolResult:
    """Update the active handoff from the current chat/session summary."""
    root = _repo_path(repo_root)
    handoff_dir = get_handoff_dir(root)

    try:
        current_provider = _normalize_provider(provider)
    except ValueError as exc:
        return _err("invalid_provider", str(exc))

    # Refuse literal secrets in free-text inputs.
    secret_check = _scan_and_reject([
        *(summary.splitlines() if summary else []),
        *(done or []), *(current or []), *(next or []), *(blockers or []),
        *(decisions or []), *(constraints or []), *(open_questions or []),
        *(important_files or []), *(privacy_notes or []),
        *(destructive_actions or []), *(needs_user_approval or []),
        *(sensitive_sources or []),
    ])
    if secret_check:
        return _err("secret_detected", secret_check)

    if not exists(handoff_dir):
        if not title:
            return _err(
                "no_active_handoff",
                "No active handoff exists. Call handoff_init first, "
                "or provide title/objective to auto-initialize.",
            )
        # Auto-initialize from capture data.
        init_result = handoff_init(
            title=title,
            objective=objective or "",
            target_provider=target_provider,
            repo_root=str(root),
            provider=provider,
        )
        if init_result.isError:
            return init_result

    handoff = load(handoff_dir)
    handoff.providers.last_updated_by = current_provider
    handoff.bump_updated_at()

    # Progress: merge without duplicating exact strings.
    handoff.progress.done = _merge_list(handoff.progress.done, done)
    handoff.progress.current = _merge_list(handoff.progress.current, current)
    handoff.progress.next = _merge_list(handoff.progress.next, next)
    handoff.progress.blockers = _merge_list(handoff.progress.blockers, blockers)

    # Context.
    handoff.context.decisions = _merge_list(handoff.context.decisions, decisions)
    handoff.context.constraints = _merge_list(handoff.context.constraints, constraints)
    handoff.context.open_questions = _merge_list(handoff.context.open_questions, open_questions)
    handoff.context.important_files = _merge_list(
        handoff.context.important_files, important_files
    )

    # Workspace.
    git_status_text = ""
    changed: list[str] = []
    if is_git_repo(root):
        raw_status = git_status(root)
        git_status_text = safe_git_status(raw_status)
        changed = safe_changed_files(changed_files(root))

    command_records = [_to_command_record(c) for c in (commands_run or [])]
    test_records = [_to_test_record(t) for t in (tests_run or [])]

    if command_records:
        handoff.workspace.commands_run.extend(command_records)
    if test_records:
        handoff.workspace.tests_run.extend(test_records)
    handoff.workspace.git_status = git_status_text
    handoff.workspace.changed_files = changed

    # Capabilities.
    used = [_to_capability_entry(c, current_provider) for c in (capabilities_used or [])]
    required = [
        _to_capability_entry(c, current_provider)
        for c in (required_next_capabilities or [])
    ]
    if used:
        handoff.capabilities.used.extend(used)
    if required:
        handoff.capabilities.required_next.extend(required)

    # Safety.
    if secrets_touched is not None:
        handoff.safety.secrets_touched = secrets_touched
    if sensitive_sources:
        handoff.safety.sensitive_sources = _merge_list(
            handoff.safety.sensitive_sources, sensitive_sources
        )
    if destructive_actions:
        handoff.safety.destructive_actions = _merge_list(
            handoff.safety.destructive_actions, destructive_actions
        )
    if needs_user_approval:
        handoff.safety.needs_user_approval = _merge_list(
            handoff.safety.needs_user_approval, needs_user_approval
        )
    if privacy_notes:
        handoff.safety.privacy_notes = _merge_list(
            handoff.safety.privacy_notes, privacy_notes
        )

    # Resume.
    if summary:
        handoff.resume.summary = _redact(summary)
    if next_prompt:
        handoff.resume.next_prompt = _redact(next_prompt)
    if target_provider:
        try:
            handoff.resume.recommended_next_provider = _normalize_provider(
                target_provider,
                current_provider,
            )
        except ValueError as exc:
            return _err("invalid_target_provider", str(exc))

    active_md = render_active(handoff)
    save(handoff, handoff_dir)
    write_active_md(active_md, handoff_dir)
    snapshot(handoff, handoff_dir, active_md)

    return _ok(
        {
            "handoff_id": handoff.handoff_id,
            "updated_at": handoff.updated_at.isoformat(),
            "paths": {
                "active_json": str(handoff_dir / "active.json"),
                "active_md": str(handoff_dir / "active.md"),
            },
        },
        f"Captured handoff **{handoff.task.title}** with {len(handoff.progress.next)} next step(s).",
    )


@mcp.tool()
def handoff_status(repo_root: str | None = None) -> CallToolResult:
    """Summarize the current handoff state."""
    root = _repo_path(repo_root)
    handoff_dir = get_handoff_dir(root)

    if not exists(handoff_dir):
        return _ok(
            {"active": False},
            "No active handoff. Use `handoff_init` to create one.",
        )

    handoff = load(handoff_dir)
    return _ok(
        {
            "active": True,
            "title": handoff.task.title,
            "status": handoff.task.status.value,
            "created_by": handoff.providers.created_by.value,
            "last_updated_by": handoff.providers.last_updated_by.value,
            "updated_at": handoff.updated_at.isoformat(),
            "next_steps": len(handoff.progress.next),
            "blockers": len(handoff.progress.blockers),
            "paths": {
                "active_json": str(handoff_dir / "active.json"),
                "active_md": str(handoff_dir / "active.md"),
            },
        },
        (
            f"**{handoff.task.title}** — `{handoff.task.status.value}`\n"
            f"Next steps: {len(handoff.progress.next)} | Blockers: {len(handoff.progress.blockers)}"
        ),
    )


@mcp.tool()
def handoff_resume(
    repo_root: str | None = None,
    provider: str | None = None,
) -> CallToolResult:
    """Read the active handoff and provide continuation context."""
    root = _repo_path(repo_root)
    handoff_dir = get_handoff_dir(root)

    if not exists(handoff_dir):
        return _err("no_active_handoff", "No active handoff to resume. Call handoff_init first.")

    try:
        current = _normalize_provider(provider)
    except ValueError as exc:
        return _err("invalid_provider", str(exc))

    handoff = load(handoff_dir)
    md_path = handoff_dir / "active.md"
    md = md_path.read_text(encoding="utf-8") if md_path.is_file() else render_active(handoff)

    warnings: list[str] = []
    if current != Provider.UNKNOWN:
        missing = check_missing_capabilities(handoff.capabilities.required_next, current)
        for cap in missing:
            warnings.append(
                f"Required capability `{cap.id}` may be missing on {current.value}; "
                f"fallback: {cap.fallback.type.value}"
            )
        if any(cap.fallback.type == FallbackType.BLOCKED for cap in missing):
            return _err(
                "blocked_capability",
                "A required capability has no safe fallback on this provider. "
                "Switch provider or add an equivalent capability.",
                markdown="\n".join(f"- {w}" for w in warnings),
            )

    return _ok(
        {
            "handoff_id": handoff.handoff_id,
            "status": handoff.task.status.value,
            "provider": current.value,
            "warnings": warnings,
            "active_md_path": str(md_path),
        },
        md,
    )


@mcp.tool()
def handoff_verify(
    repo_root: str | None = None,
    provider: str | None = None,
    strict: bool = False,
) -> CallToolResult:
    """Check whether a handoff is safe and complete enough to switch providers."""
    root = _repo_path(repo_root)
    handoff_dir = get_handoff_dir(root)

    if not exists(handoff_dir):
        return _err("no_active_handoff", "No active handoff to verify. Call handoff_init first.")

    try:
        current = _normalize_provider(provider)
    except ValueError as exc:
        return _err("invalid_provider", str(exc))

    handoff = load(handoff_dir)
    result = verify(handoff, current, root)

    if strict and result.warnings:
        result.ok = False

    fixes = []
    if not handoff.task.objective:
        fixes.append("Add an objective to the handoff.")
    if handoff.task.status == TaskStatus.IN_PROGRESS and not handoff.progress.next:
        fixes.append("Add at least one next step.")
    if not handoff.workspace.tests_run:
        fixes.append("Record tests run or explicitly mark them skipped.")
    if not handoff.workspace.changed_files and handoff.workspace.git_status:
        fixes.append("Capture changed files.")

    return _ok(
        {
            "pass": result.ok,
            "warnings": result.warnings,
            "errors": result.errors,
            "suggested_fixes": fixes,
        },
        ("PASS" if result.ok else "FAIL") + "\n" + "\n".join(
            [f"- WARN: {w}" for w in result.warnings]
            + [f"- FAIL: {e}" for e in result.errors]
            + (["Suggested fixes:"] + [f"  - {f}" for f in fixes] if fixes else [])
        ),
    )


@mcp.tool()
def handoff_export(
    target_provider: str,
    repo_root: str | None = None,
) -> CallToolResult:
    """Create a continuation prompt for a target provider."""
    root = _repo_path(repo_root)
    handoff_dir = get_handoff_dir(root)

    if not exists(handoff_dir):
        return _err("no_active_handoff", "No active handoff to export. Call handoff_init first.")

    try:
        target = _normalize_provider(target_provider)
    except ValueError as exc:
        return _err("invalid_target_provider", str(exc))

    handoff = load(handoff_dir)
    path = export_to(handoff, target.value, handoff_dir)
    preview = path.read_text(encoding="utf-8")[:1200]

    return _ok(
        {
            "target_provider": target.value,
            "export_path": str(path),
        },
        f"Exported continuation prompt for **{target.value}** to `{path}`.\n\nPreview:\n\n{preview}",
    )


@mcp.tool()
def handoff_close(
    repo_root: str | None = None,
    provider: str | None = None,
    summary: str | None = None,
) -> CallToolResult:
    """Mark the handoff complete and archive it."""
    root = _repo_path(repo_root)
    handoff_dir = get_handoff_dir(root)

    if not exists(handoff_dir):
        return _err("no_active_handoff", "No active handoff to close. Call handoff_init first.")

    try:
        current = _normalize_provider(provider)
    except ValueError as exc:
        return _err("invalid_provider", str(exc))

    handoff = load(handoff_dir)
    handoff.providers.last_updated_by = current
    if summary:
        handoff.resume.summary = _redact(summary)
    handoff.resume.summary = handoff.resume.summary or "Task closed."

    snap = close_handoff(handoff, handoff_dir)
    return _ok(
        {"archive_path": str(snap)},
        f"Closed handoff and archived to `{snap}`.",
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
