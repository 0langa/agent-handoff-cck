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


def test_capture_accepts_common_result_aliases(tmp_path: Path) -> None:
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
    result = runner.invoke(
        main,
        [
            "capture",
            "--repo-root",
            str(tmp_path),
            "--provider",
            "kimi-code",
            "--next",
            "export",
            "--command",
            "pytest|run tests|passed",
            "--test",
            "pytest|success|all green",
        ],
    )
    assert result.exit_code == 0, result.output


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


GITHUB_TOKEN = "ghp_" + "aB3dE5fG7hJ9kL1mN0" * 2  # built at runtime for secret scanners
CLI_SECRETS = [
    GITHUB_TOKEN,
    "abc123secret456",
    "hunter2pass",
    "9f8e7d6c5b4a",
    "Zx9Qw8Er7Ty6",
    "abcdefghijklmnop1234",
    "t0ps3cr3t",
    "Tr0ub4dor",
    "pgS3cret99",
]


def _written_text(handoff_dir: Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(handoff_dir.rglob("*")) if p.is_file()
    )


def test_cli_redacts_secrets_in_everything_it_writes(tmp_path: Path) -> None:
    runner = CliRunner()
    root = ["--repo-root", str(tmp_path)]
    result = runner.invoke(
        main,
        [
            "init",
            "--title",
            f"Rotate {GITHUB_TOKEN}",
            "--objective",
            "Move API_KEY=abc123secret456 to the vault",
            *root,
            "--provider",
            "codex",
        ],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        main,
        [
            "capture",
            *root,
            "--provider",
            "codex",
            "--done",
            "pushed to https://deploy:hunter2pass@git.example.com/r.git",
            "--next",
            "call the API with --api-key 9f8e7d6c5b4a",
            "--decision",
            '{"client_secret": "Zx9Qw8Er7Ty6"}',
            "--command",
            "curl -H 'Authorization: Bearer abcdefghijklmnop1234'|call api|ok",
            "--test",
            "pytest --token=t0ps3cr3t|passed|all green",
            "--privacy-note",
            'password: "Tr0ub4dor&3xyz"',
            "--summary",
            "Ran the migration with PGPASSWORD=pgS3cret99",
            "--next-prompt",
            f"Resume with GITHUB_TOKEN={GITHUB_TOKEN}",
        ],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(main, ["export", "claude-code", *root])
    assert result.exit_code == 0, result.output

    handoff_dir = tmp_path / ".handoff"
    assert (handoff_dir / "exports" / "claude-code.md").is_file()
    assert list((handoff_dir / "history").glob("*.md"))
    written = _written_text(handoff_dir)
    assert written.count("[REDACTED]") >= len(CLI_SECRETS)
    shown = "".join(
        runner.invoke(main, args).output
        for args in (["status", *root], ["resume", *root, "--provider", "codex"])
    )
    assert "[REDACTED]" in shown
    for secret in CLI_SECRETS:
        assert secret not in written, secret
        assert secret not in shown, secret

    result = runner.invoke(main, ["close", *root, "--provider", "codex"])
    assert result.exit_code == 0, result.output
    archived = _written_text(handoff_dir)
    for secret in CLI_SECRETS:
        assert secret not in archived, secret


def test_cli_and_mcp_store_the_same_redacted_command(tmp_path: Path) -> None:
    from agent_handoff.mcp_server import handoff_capture, handoff_init
    from agent_handoff.store import get_handoff_dir, load

    command = (
        "curl --token abc123def456 -H 'X-Api-Key: Zx9Qw8Er7Ty6' "
        "https://bot:t0ken99@api.example.com/v1"
    )
    cli_root, mcp_root = tmp_path / "cli", tmp_path / "mcp"
    runner = CliRunner()
    runner.invoke(
        main, ["init", "--title", "t", "--repo-root", str(cli_root), "--provider", "codex"]
    )
    result = runner.invoke(
        main,
        [
            "capture",
            "--repo-root",
            str(cli_root),
            "--provider",
            "codex",
            "--command",
            f"{command}|call api|ok",
        ],
    )
    assert result.exit_code == 0, result.output
    assert not handoff_init(title="t", repo_root=str(mcp_root), provider="codex").isError
    assert not handoff_capture(
        repo_root=str(mcp_root),
        provider="codex",
        commands_run=[{"command": command, "purpose": "call api", "result": "ok"}],
    ).isError

    cli_command = load(get_handoff_dir(cli_root)).workspace.commands_run[0].command
    mcp_command = load(get_handoff_dir(mcp_root)).workspace.commands_run[0].command
    assert cli_command == mcp_command == (
        "curl --token [REDACTED] -H 'X-Api-Key: [REDACTED]' "
        "https://bot:[REDACTED]@api.example.com/v1"
    )
