"""Tests for handoff store operations."""

from pathlib import Path

from agent_handoff import store
from agent_handoff.export import export_to
from agent_handoff.render import render_active
from agent_handoff.schema import CommandRecord, HandoffSchema


def test_every_write_is_redacted(tmp_path: Path) -> None:
    handoff_dir = tmp_path / ".handoff"
    h = HandoffSchema(task={"title": "test", "objective": "export GITHUB_TOKEN=abcdefgh12345"})
    h.workspace.commands_run.append(CommandRecord(command="mytool --password hunter2"))
    markdown = render_active(h)
    assert "abcdefgh12345" in markdown  # rendering itself does not redact

    store.save(h, handoff_dir)
    store.write_active_md(markdown, handoff_dir)
    store.snapshot(h, handoff_dir, markdown)
    export_to(h, "codex", handoff_dir)

    written = [p for p in handoff_dir.rglob("*") if p.is_file()]
    assert len(written) == 5  # active.json, active.md, history .json/.md, export
    for path in written:
        text = path.read_text(encoding="utf-8")
        assert "abcdefgh12345" not in text, path
        assert "hunter2" not in text, path
        assert "[REDACTED]" in text, path
    loaded = store.load(handoff_dir)
    assert loaded.task.objective == "export GITHUB_TOKEN=[REDACTED]"
    assert loaded.workspace.commands_run[0].command == "mytool --password [REDACTED]"


def test_save_and_load(tmp_path: Path) -> None:
    handoff_dir = tmp_path / ".handoff"
    h = HandoffSchema(task={"title": "test", "objective": "o"})
    path = store.save(h, handoff_dir)
    assert path.is_file()

    loaded = store.load(handoff_dir)
    assert loaded.task.title == "test"


def test_active_md_written(tmp_path: Path) -> None:
    handoff_dir = tmp_path / ".handoff"
    h = HandoffSchema(task={"title": "test"})
    store.save(h, handoff_dir)
    store.write_active_md("# test", handoff_dir)
    assert (handoff_dir / "active.md").is_file()


def test_snapshot_creates_history(tmp_path: Path) -> None:
    handoff_dir = tmp_path / ".handoff"
    h = HandoffSchema(task={"title": "test"})
    snap = store.snapshot(h, handoff_dir, "# test")
    assert snap.is_file()
    assert snap.parent.name == "history"
    assert snap.with_suffix(".md").read_text(encoding="utf-8") == "# test\n"


def test_close_archives_active(tmp_path: Path) -> None:
    handoff_dir = tmp_path / ".handoff"
    h = HandoffSchema(task={"title": "test"})
    store.save(h, handoff_dir)
    store.write_active_md("# test", handoff_dir)
    store.close(h, handoff_dir)
    assert not (handoff_dir / "active.json").is_file()
    assert not (handoff_dir / "active.md").is_file()
    assert (handoff_dir / "history").exists()


def test_validate_raw_ok(tmp_path: Path) -> None:
    ok, errors = store.validate_raw({"task": {"title": "ok"}})
    assert ok
    assert not errors


def test_validate_raw_bad_status(tmp_path: Path) -> None:
    ok, errors = store.validate_raw({"task": {"title": "ok", "status": "weird"}})
    assert not ok
    assert any("status" in e for e in errors)
