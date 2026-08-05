"""Command-line interface for agent-handoff."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from . import __version__
from .capabilities import check_missing_capabilities
from .export import export_to
from .git_context import changed_files, git_status, is_git_repo
from .privacy import safe_changed_files, safe_git_status
from .render import render_active
from .schema import (
    CapabilityEntry,
    CommandRecord,
    CommandResult,
    FallbackType,
    HandoffSchema,
    ProgressBlock,
    TaskStatus,
    TestRecord,
    TestResult,
    WorkspaceBlock,
    parse_provider,
)
from .store import close as close_handoff
from .store import exists, get_handoff_dir, load, save, snapshot, write_active_md
from .verify import verify


def _provider_option() -> click.Option:
    return click.option(
        "--provider",
        default=lambda: _detect_provider(),
        help="Current provider: codex, claude-code, kimi-code.",
    )


def _detect_provider() -> str:
    env = os.environ.get("AGENT_HANDOFF_PROVIDER", "").lower()
    if env in {"codex", "claude-code", "kimi-code"}:
        return env
    # Heuristic: some clients set environment variables.
    if os.environ.get("CODEX_ROOT") or os.environ.get("OPENAI_CODEX"):
        return "codex"
    if os.environ.get("CLAUDE_CODE"):
        return "claude-code"
    if os.environ.get("KIMI_CODE"):
        return "kimi-code"
    return "unknown"


@click.group()
@click.version_option(version=__version__, prog_name="agent-handoff")
def main() -> None:
    """Cross-agent handoff CLI."""


@main.command()
@click.option("--title", required=True, help="Task title.")
@click.option("--objective", default="", help="Task objective.")
@click.option("--repo-root", default=".", help="Repository root.")
@click.option("--provider", default=lambda: _detect_provider(), help="Creating provider.")
@click.option("--target-provider", default=None, help="Recommended next provider.")
def init(
    title: str,
    objective: str,
    repo_root: str,
    provider: str,
    target_provider: str | None,
) -> None:
    """Create a new handoff record."""
    root = Path(repo_root).resolve()
    handoff_dir = get_handoff_dir(root)
    if exists(handoff_dir):
        click.echo("Handoff already exists. Use 'capture' to update it.", err=True)
        sys.exit(1)

    handoff = HandoffSchema(
        task={"title": title, "objective": objective, "status": TaskStatus.IN_PROGRESS.value},
        providers={
            "created_by": provider,
            "last_updated_by": provider,
            "compatible_with": ["codex", "claude-code", "kimi-code"],
        },
        context={"repo_root": str(root)},
    )
    if target_provider:
        handoff.resume.recommended_next_provider = parse_provider(target_provider)

    save(handoff, handoff_dir)
    write_active_md(render_active(handoff), handoff_dir)
    click.echo(f"Initialized handoff at {handoff_dir / 'active.json'}")


@main.command()
@click.option("--repo-root", default=".", help="Repository root.")
@click.option("--provider", default=lambda: _detect_provider(), help="Current provider.")
@click.option("--done", "done_items", multiple=True, help="Completed item.")
@click.option("--current", "current_items", multiple=True, help="In-progress item.")
@click.option("--next", "next_items", multiple=True, help="Next item.")
@click.option("--blocker", "blockers", multiple=True, help="Blocker item.")
@click.option("--decision", "decisions", multiple=True, help="Decision item.")
@click.option("--constraint", "constraints", multiple=True, help="Constraint item.")
@click.option("--question", "questions", multiple=True, help="Open question.")
@click.option("--command", "commands", multiple=True, help="Command run (format: cmd|purpose|result).")
@click.option("--test", "tests", multiple=True, help="Test run (format: cmd|result|summary).")
@click.option("--important-file", "important_files", multiple=True, help="Important file path.")
@click.option("--capability", "capabilities", multiple=True, help="Capability (JSON string).")
@click.option("--secrets-touched/--no-secrets-touched", default=None, help="Whether secrets were touched.")
@click.option("--destructive-action", "destructive_actions", multiple=True, help="Destructive action recorded.")
@click.option("--needs-approval", "needs_approval", multiple=True, help="Action needing user approval.")
@click.option("--privacy-note", "privacy_notes", multiple=True, help="Privacy note.")
@click.option("--summary", default="", help="Resume summary.")
@click.option("--next-prompt", default="", help="Next provider prompt.")
def capture(
    repo_root: str,
    provider: str,
    done_items: tuple[str, ...],
    current_items: tuple[str, ...],
    next_items: tuple[str, ...],
    blockers: tuple[str, ...],
    decisions: tuple[str, ...],
    constraints: tuple[str, ...],
    questions: tuple[str, ...],
    commands: tuple[str, ...],
    tests: tuple[str, ...],
    important_files: tuple[str, ...],
    capabilities: tuple[str, ...],
    secrets_touched: bool | None,
    destructive_actions: tuple[str, ...],
    needs_approval: tuple[str, ...],
    privacy_notes: tuple[str, ...],
    summary: str,
    next_prompt: str,
) -> None:
    """Update handoff from current work state."""
    root = Path(repo_root).resolve()
    handoff_dir = get_handoff_dir(root)
    if not exists(handoff_dir):
        click.echo("No active handoff. Run 'init' first.", err=True)
        sys.exit(1)

    handoff = load(handoff_dir)
    handoff.providers.last_updated_by = parse_provider(provider)
    handoff.bump_updated_at()

    # Update progress.
    if done_items or current_items or next_items or blockers:
        handoff.progress = ProgressBlock(
            done=list(done_items) or handoff.progress.done,
            current=list(current_items) or handoff.progress.current,
            next=list(next_items) or handoff.progress.next,
            blockers=list(blockers) or handoff.progress.blockers,
        )
    if done_items:
        handoff.progress.done = list(done_items)
    if current_items:
        handoff.progress.current = list(current_items)
    if next_items:
        handoff.progress.next = list(next_items)
    if blockers:
        handoff.progress.blockers = list(blockers)

    # Update context.
    if decisions:
        handoff.context.decisions.extend(decisions)
    if constraints:
        handoff.context.constraints.extend(constraints)
    if questions:
        handoff.context.open_questions.extend(questions)
    if important_files:
        handoff.context.important_files.extend(important_files)

    # Capture workspace.
    git_status_text = ""
    changed: list[str] = []
    if is_git_repo(root):
        raw_status = git_status(root)
        git_status_text = safe_git_status(raw_status)
        changed = safe_changed_files(changed_files(root))

    command_records = [_parse_command(c) for c in commands]
    test_records = [_parse_test(t) for t in tests]

    handoff.workspace = WorkspaceBlock(
        git_status=git_status_text,
        changed_files=changed,
        commands_run=command_records or handoff.workspace.commands_run,
        tests_run=test_records or handoff.workspace.tests_run,
    )
    if command_records:
        handoff.workspace.commands_run = command_records
    if test_records:
        handoff.workspace.tests_run = test_records

    # Capabilities.
    parsed_caps = [_parse_capability(c) for c in capabilities]
    if parsed_caps:
        handoff.capabilities.used.extend(parsed_caps)
        for cap in parsed_caps:
            if cap.required_to_continue:
                handoff.capabilities.required_next.append(cap)

    # Safety.
    if secrets_touched is not None:
        handoff.safety.secrets_touched = secrets_touched
    if destructive_actions:
        handoff.safety.destructive_actions.extend(destructive_actions)
    if needs_approval:
        handoff.safety.needs_user_approval.extend(needs_approval)
    if privacy_notes:
        handoff.safety.privacy_notes.extend(privacy_notes)

    # Resume.
    if summary:
        handoff.resume.summary = summary
    if next_prompt:
        handoff.resume.next_prompt = next_prompt

    active_md = render_active(handoff)
    save(handoff, handoff_dir)
    write_active_md(active_md, handoff_dir)
    snapshot(handoff, handoff_dir, active_md)
    click.echo(f"Captured handoff at {handoff_dir / 'active.json'}")


@main.command()
@click.option("--repo-root", default=".", help="Repository root.")
def status(repo_root: str) -> None:
    """Show current handoff status."""
    root = Path(repo_root).resolve()
    handoff_dir = get_handoff_dir(root)
    if not exists(handoff_dir):
        click.echo("No active handoff.")
        return
    handoff = load(handoff_dir)
    click.echo(f"Title: {handoff.task.title}")
    click.echo(f"Status: {handoff.task.status.value}")
    click.echo(f"Created by: {handoff.providers.created_by.value}")
    click.echo(f"Last updated by: {handoff.providers.last_updated_by.value}")
    click.echo(f"Updated at: {handoff.updated_at.isoformat()}")
    click.echo(f"Next steps: {len(handoff.progress.next)}")
    click.echo(f"Blockers: {len(handoff.progress.blockers)}")


@main.command()
@click.option("--repo-root", default=".", help="Repository root.")
@click.option("--provider", default=lambda: _detect_provider(), help="Current provider.")
def resume(repo_root: str, provider: str) -> None:
    """Continue from latest handoff."""
    root = Path(repo_root).resolve()
    handoff_dir = get_handoff_dir(root)
    if not exists(handoff_dir):
        click.echo("No active handoff to resume.", err=True)
        sys.exit(1)
    handoff = load(handoff_dir)
    current = parse_provider(provider)

    missing = check_missing_capabilities(handoff.capabilities.required_next, current)
    if missing:
        click.echo("WARNING: required capabilities may be missing on this provider:", err=True)
        for cap in missing:
            click.echo(f"  - {cap.id}: {cap.fallback.type.value} ({cap.fallback.details})", err=True)
        if any(cap.fallback.type == FallbackType.BLOCKED for cap in missing):
            click.echo("Cannot continue safely. Switch provider or add equivalent capability.", err=True)
            sys.exit(2)

    md_path = handoff_dir / "active.md"
    if md_path.is_file():
        click.echo(md_path.read_text(encoding="utf-8"))
    else:
        click.echo(render_active(handoff))


@main.command()
@click.option("--repo-root", default=".", help="Repository root.")
@click.option("--provider", default=lambda: _detect_provider(), help="Current provider.")
@click.option("--strict/--no-strict", default=False, help="Treat warnings as failures.")
def verify_cmd(repo_root: str, provider: str, strict: bool) -> None:
    """Verify handoff completeness."""
    root = Path(repo_root).resolve()
    handoff_dir = get_handoff_dir(root)
    if not exists(handoff_dir):
        click.echo("No active handoff.", err=True)
        sys.exit(1)
    handoff = load(handoff_dir)
    result = verify(handoff, parse_provider(provider), root)

    for warning in result.warnings:
        click.echo(f"WARN: {warning}")
    for error in result.errors:
        click.echo(f"FAIL: {error}")

    if strict and result.warnings:
        result.ok = False

    if result.ok:
        click.echo("PASS")
    else:
        sys.exit(1)


@main.command("export")
@click.argument("target")
@click.option("--repo-root", default=".", help="Repository root.")
def export_cmd(target: str, repo_root: str) -> None:
    """Export continuation prompt for target provider."""
    root = Path(repo_root).resolve()
    handoff_dir = get_handoff_dir(root)
    if not exists(handoff_dir):
        click.echo("No active handoff.", err=True)
        sys.exit(1)
    handoff = load(handoff_dir)
    path = export_to(handoff, target, handoff_dir)
    click.echo(f"Exported to {path}")


@main.command()
@click.option("--repo-root", default=".", help="Repository root.")
@click.option("--provider", default=lambda: _detect_provider(), help="Current provider.")
def close(repo_root: str, provider: str) -> None:
    """Mark task complete and archive."""
    root = Path(repo_root).resolve()
    handoff_dir = get_handoff_dir(root)
    if not exists(handoff_dir):
        click.echo("No active handoff.", err=True)
        sys.exit(1)
    handoff = load(handoff_dir)
    handoff.providers.last_updated_by = parse_provider(provider)
    handoff.resume.summary = handoff.resume.summary or "Task closed."
    snap = close_handoff(handoff, handoff_dir)
    click.echo(f"Closed and archived to {snap}")


def _parse_command(text: str) -> CommandRecord:
    parts = text.split("|", 2)
    return CommandRecord(
        command=parts[0],
        purpose=parts[1] if len(parts) > 1 else None,
        result=_parse_command_result(parts[2] if len(parts) > 2 else None),
    )


def _parse_test(text: str) -> TestRecord:
    parts = text.split("|", 2)
    return TestRecord(
        command=parts[0],
        result=_parse_test_result(parts[1] if len(parts) > 1 else None),
        summary=parts[2] if len(parts) > 2 else None,
    )


def _parse_capability(text: str) -> CapabilityEntry:
    data = json.loads(text)
    return CapabilityEntry.model_validate(data)


def _parse_command_result(value: str | None) -> CommandResult:
    normalized = (value or "unknown").strip().lower()
    aliases = {
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
    return aliases.get(normalized, CommandResult.UNKNOWN)


def _parse_test_result(value: str | None) -> TestResult:
    normalized = (value or "unknown").strip().lower()
    aliases = {
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
    return aliases.get(normalized, TestResult.UNKNOWN)


if __name__ == "__main__":
    main()
