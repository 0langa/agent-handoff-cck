"""Tests for handoff verification."""

from pathlib import Path

import pytest

from agent_handoff.schema import (
    CapabilityEntry,
    CapabilityType,
    FallbackType,
    HandoffSchema,
    Provider,
    TaskStatus,
)
from agent_handoff.verify import verify


def test_verify_passes_complete_handoff() -> None:
    h = HandoffSchema(
        task={"title": "t", "objective": "o", "status": TaskStatus.COMPLETE.value},
        progress={"done": ["a"]},
        workspace={"tests_run": [{"command": "pytest", "result": "passed"}]},
    )
    result = verify(h)
    assert result.ok


def test_verify_fails_missing_objective() -> None:
    h = HandoffSchema(task={"title": "t"})
    result = verify(h)
    assert not result.ok
    assert any("objective" in e for e in result.errors)


def test_verify_fails_in_progress_without_next() -> None:
    h = HandoffSchema(task={"title": "t", "objective": "o"})
    result = verify(h)
    assert not result.ok
    assert any("next" in e for e in result.errors)


def test_verify_warns_no_tests() -> None:
    h = HandoffSchema(
        task={"title": "t", "objective": "o", "status": TaskStatus.COMPLETE.value},
        progress={"done": ["a"]},
    )
    result = verify(h)
    assert result.ok
    assert any("tests" in w for w in result.warnings)


def test_verify_fails_blocked_capability() -> None:
    h = HandoffSchema(
        task={"title": "t", "objective": "o", "status": TaskStatus.IN_PROGRESS.value},
        progress={"next": ["step"]},
        capabilities={
            "required_next": [
                CapabilityEntry(
                    provider=Provider.CODEX,
                    type=CapabilityType.PLUGIN,
                    id="gmail@openai-curated-remote",
                    required_to_continue=True,
                    fallback={"type": FallbackType.BLOCKED, "details": "no mail tool"},
                )
            ]
        },
    )
    result = verify(h)
    assert not result.ok
    assert any("blocked" in e for e in result.errors)


def test_verify_does_not_warn_stale_git_for_non_git_directory(tmp_path: Path) -> None:
    h = HandoffSchema(
        task={"title": "t", "objective": "o", "status": TaskStatus.IN_PROGRESS.value},
        progress={"next": ["step"]},
        workspace={"git_status": ""},
    )
    result = verify(h, repo_root=tmp_path)
    assert not any("git status differs" in w for w in result.warnings)
