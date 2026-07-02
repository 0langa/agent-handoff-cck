"""Tests for the MCP server tools."""

import asyncio
import json
from pathlib import Path

import pytest

from agent_handoff.mcp_server import mcp


def _call(name: str, arguments: dict) -> dict:
    result = asyncio.run(mcp.call_tool(name, arguments))
    text_blocks = [c.text for c in result.content if c.type == "text"]
    return {
        "is_error": result.isError,
        "json": json.loads(text_blocks[0]) if text_blocks else None,
        "markdown": text_blocks[1] if len(text_blocks) > 1 else "",
    }


def test_status_no_active_handoff(tmp_path: Path) -> None:
    result = _call("handoff_status", {"repo_root": str(tmp_path)})
    assert not result["is_error"]
    assert result["json"]["ok"] is True
    assert result["json"]["data"]["active"] is False


def test_init_creates_files(tmp_path: Path) -> None:
    result = _call(
        "handoff_init",
        {
            "title": "Test task",
            "objective": "Do the thing",
            "repo_root": str(tmp_path),
            "provider": "codex",
        },
    )
    assert not result["is_error"]
    assert result["json"]["ok"] is True
    assert (tmp_path / ".handoff" / "active.json").is_file()
    assert (tmp_path / ".handoff" / "active.md").is_file()


def test_init_refuses_overwrite_without_force(tmp_path: Path) -> None:
    _call("handoff_init", {"title": "First", "repo_root": str(tmp_path), "provider": "codex"})
    result = _call("handoff_init", {"title": "Second", "repo_root": str(tmp_path), "provider": "codex"})
    assert result["is_error"]
    assert result["json"]["ok"] is False
    assert result["json"]["error"]["code"] == "handoff_exists"


def test_init_force_overwrites(tmp_path: Path) -> None:
    _call("handoff_init", {"title": "First", "repo_root": str(tmp_path), "provider": "codex"})
    result = _call(
        "handoff_init",
        {
            "title": "Second",
            "repo_root": str(tmp_path),
            "provider": "codex",
            "force": True,
        },
    )
    assert not result["is_error"]
    assert result["json"]["data"]["handoff_id"]


def test_capture_updates_progress_and_history(tmp_path: Path) -> None:
    _call(
        "handoff_init",
        {"title": "Test", "objective": "Obj", "repo_root": str(tmp_path), "provider": "codex"},
    )
    result = _call(
        "handoff_capture",
        {
            "repo_root": str(tmp_path),
            "provider": "codex",
            "done": ["step A"],
            "next": ["step B"],
            "tests_run": [{"command": "pytest", "result": "passed"}],
        },
    )
    assert not result["is_error"]
    assert result["json"]["ok"] is True
    assert (tmp_path / ".handoff" / "history").exists()


def test_capture_auto_initializes_with_title(tmp_path: Path) -> None:
    result = _call(
        "handoff_capture",
        {
            "repo_root": str(tmp_path),
            "provider": "kimi-code",
            "title": "Auto init",
            "objective": "Test auto-init",
            "next": ["do something"],
        },
    )
    assert not result["is_error"]
    assert (tmp_path / ".handoff" / "active.json").is_file()


def test_capture_requires_init_without_title(tmp_path: Path) -> None:
    result = _call("handoff_capture", {"repo_root": str(tmp_path), "provider": "codex"})
    assert result["is_error"]
    assert result["json"]["error"]["code"] == "no_active_handoff"


def test_verify_passes_and_fails(tmp_path: Path) -> None:
    _call(
        "handoff_init",
        {"title": "Test", "objective": "Obj", "repo_root": str(tmp_path), "provider": "codex"},
    )
    _call(
        "handoff_capture",
        {
            "repo_root": str(tmp_path),
            "provider": "codex",
            "next": ["step"],
            "tests_run": [{"command": "pytest", "result": "passed"}],
        },
    )
    result = _call("handoff_verify", {"repo_root": str(tmp_path), "provider": "kimi-code"})
    assert not result["is_error"]
    assert result["json"]["data"]["pass"] is True


def test_export_creates_target_file(tmp_path: Path) -> None:
    _call(
        "handoff_init",
        {"title": "Test", "objective": "Obj", "repo_root": str(tmp_path), "provider": "codex"},
    )
    _call(
        "handoff_capture",
        {
            "repo_root": str(tmp_path),
            "provider": "codex",
            "next": ["step"],
        },
    )
    result = _call("handoff_export", {"target_provider": "claude-code", "repo_root": str(tmp_path)})
    assert not result["is_error"]
    assert (tmp_path / ".handoff" / "exports" / "claude-code.md").is_file()


def test_close_archives(tmp_path: Path) -> None:
    _call(
        "handoff_init",
        {"title": "Test", "objective": "Obj", "repo_root": str(tmp_path), "provider": "codex"},
    )
    result = _call("handoff_close", {"repo_root": str(tmp_path), "provider": "codex"})
    assert not result["is_error"]
    assert not (tmp_path / ".handoff" / "active.json").is_file()
    assert (tmp_path / ".handoff" / "history").exists()


def test_invalid_provider_rejected(tmp_path: Path) -> None:
    result = _call(
        "handoff_init",
        {"title": "Test", "repo_root": str(tmp_path), "provider": "not-a-provider"},
    )
    assert result["is_error"]
    assert result["json"]["error"]["code"] == "invalid_provider"


def test_secret_detected_in_capture(tmp_path: Path) -> None:
    result = _call(
        "handoff_capture",
        {
            "repo_root": str(tmp_path),
            "provider": "codex",
            "title": "Leak",
            "summary": "api_key=super_secret_value_12345",
        },
    )
    assert result["is_error"]
    assert result["json"]["error"]["code"] == "secret_detected"
