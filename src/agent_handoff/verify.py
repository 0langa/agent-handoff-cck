"""Verify handoff completeness and safety before switching providers."""

from __future__ import annotations

from pathlib import Path

from . import store
from .capabilities import check_missing_capabilities
from .git_context import git_status
from .schema import FallbackType, HandoffSchema, Provider, TaskStatus


class VerifyResult:
    def __init__(self) -> None:
        self.ok = True
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def verify(
    handoff: HandoffSchema,
    current_provider: Provider = Provider.UNKNOWN,
    repo_root: Path | str | None = None,
) -> VerifyResult:
    result = VerifyResult()

    # Schema-level checks.
    if not handoff.handoff_id:
        result.fail("handoffId missing")
    if not handoff.task.title:
        result.fail("task.title missing")
    if not handoff.task.objective:
        result.fail("task.objective missing")
    if not handoff.task.status:
        result.fail("task.status missing")

    if handoff.task.status == TaskStatus.IN_PROGRESS:
        if not handoff.progress.next and not handoff.resume.next_prompt:
            result.fail("in-progress handoff has no next actions or resume prompt")

    # Progress checks.
    if not handoff.progress.done and not handoff.progress.current:
        result.warn("no progress recorded (done or current)")

    # Workspace checks.
    if not handoff.workspace.changed_files and handoff.workspace.git_status:
        result.warn("git status present but changed_files empty")

    if not handoff.workspace.tests_run and handoff.task.status != TaskStatus.NOT_STARTED:
        result.warn("no tests recorded; mark skipped if not applicable")

    # Capability checks.
    for cap in handoff.capabilities.required_next:
        if cap.required_to_continue:
            if not cap.fallback or not cap.fallback.type:
                result.fail(f"required capability '{cap.id}' has no fallback")
            elif cap.fallback.type == FallbackType.BLOCKED:
                result.fail(f"required capability '{cap.id}' is blocked: {cap.fallback.details}")

    # Missing capabilities for current provider.
    if current_provider != Provider.UNKNOWN:
        missing = check_missing_capabilities(handoff.capabilities.required_next, current_provider)
        for cap in missing:
            result.warn(
                f"capability '{cap.id}' may be missing on {current_provider.value}; "
                f"fallback: {cap.fallback.type.value}"
            )

    # Safety checks.
    if handoff.safety.secrets_touched and not handoff.safety.sensitive_sources:
        result.warn("secrets_touched=true but no sensitive_sources listed")

    for action in handoff.safety.destructive_actions:
        if "needs user approval" not in action.lower():
            result.warn(f"destructive action should require user approval: {action}")

    # Stale git status.
    if repo_root and store.exists(store.get_handoff_dir(repo_root)):
        try:
            current_status = git_status(repo_root)
            if current_status != (handoff.workspace.git_status or ""):
                result.warn("workspace git status differs from captured status")
        except Exception:
            pass

    return result
