"""Tests for Markdown rendering and exports."""

from pathlib import Path

from agent_handoff.export import export_to
from agent_handoff.render import render_active, render_export
from agent_handoff.schema import HandoffSchema, Provider


def test_render_active_includes_title() -> None:
    h = HandoffSchema(task={"title": "Fix auth", "objective": "Resolve token expiry"})
    md = render_active(h)
    assert "# Fix auth" in md
    assert "Resolve token expiry" in md


def test_render_active_lists_progress() -> None:
    h = HandoffSchema(
        task={"title": "t"},
        progress={"done": ["a"], "current": ["b"], "next": ["c"], "blockers": ["d"]},
    )
    md = render_active(h)
    assert "- a" in md
    assert "- c" in md
    assert "- d" in md


def test_export_codex_includes_provider_name() -> None:
    h = HandoffSchema(task={"title": "t", "objective": "o"})
    md = render_export(h, Provider.CODEX)
    assert "Codex" in md
    assert "t" in md


def test_export_claude_code_includes_provider_name() -> None:
    h = HandoffSchema(task={"title": "t"})
    md = render_export(h, Provider.CLAUDE_CODE)
    assert "Claude Code" in md


def test_export_kimi_code_includes_provider_name() -> None:
    h = HandoffSchema(task={"title": "t"})
    md = render_export(h, Provider.KIMI_CODE)
    assert "Kimi Code" in md


def test_export_generic_for_unknown_provider() -> None:
    h = HandoffSchema(task={"title": "t"})
    md = render_export(h, Provider.UNKNOWN)
    assert "Continuation Prompt" in md


def test_export_to_generic_creates_unknown_export(tmp_path: Path) -> None:
    h = HandoffSchema(task={"title": "t"})
    path = export_to(h, "generic", tmp_path / ".handoff")
    assert path.name == "unknown.md"
    assert path.is_file()
