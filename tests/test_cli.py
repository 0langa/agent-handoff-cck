"""Smoke tests for the CLI."""

from pathlib import Path

from click.testing import CliRunner

from agent_handoff.cli import main


def test_init_creates_active_files(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init",
            "--title",
            "test",
            "--objective",
            "objective",
            "--repo-root",
            str(tmp_path),
            "--provider",
            "codex",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".handoff" / "active.json").is_file()
    assert (tmp_path / ".handoff" / "active.md").is_file()


def test_status_shows_handoff(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        main,
        ["init", "--title", "test", "--repo-root", str(tmp_path), "--provider", "codex"],
    )
    result = runner.invoke(main, ["status", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "test" in result.output


def test_verify_passes(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        main,
        [
            "init",
            "--title",
            "test",
            "--objective",
            "objective",
            "--repo-root",
            str(tmp_path),
            "--provider",
            "codex",
        ],
    )
    runner.invoke(
        main,
        [
            "capture",
            "--repo-root",
            str(tmp_path),
            "--provider",
            "codex",
            "--next",
            "do thing",
            "--test",
            "pytest|passed|all green",
        ],
    )
    result = runner.invoke(main, ["verify", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


def test_export_creates_file(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        main,
        [
            "init",
            "--title",
            "test",
            "--objective",
            "objective",
            "--repo-root",
            str(tmp_path),
            "--provider",
            "codex",
        ],
    )
    runner.invoke(
        main,
        ["capture", "--repo-root", str(tmp_path), "--provider", "codex", "--next", "do thing"],
    )
    result = runner.invoke(main, ["export", "claude-code", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".handoff" / "exports" / "claude-code.md").is_file()


def test_close_archives(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        main,
        [
            "init",
            "--title",
            "test",
            "--objective",
            "objective",
            "--repo-root",
            str(tmp_path),
            "--provider",
            "codex",
        ],
    )
    result = runner.invoke(main, ["close", "--repo-root", str(tmp_path), "--provider", "codex"])
    assert result.exit_code == 0, result.output
    assert not (tmp_path / ".handoff" / "active.json").is_file()
