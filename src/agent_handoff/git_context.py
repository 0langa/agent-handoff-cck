"""Git workspace context capture."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: Path | str | None = None) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=30,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "git not found"
    except subprocess.TimeoutExpired:
        return 124, "", "git command timed out"


def is_git_repo(cwd: Path | str | None = None) -> bool:
    code, _, _ = _run_git(["rev-parse", "--git-dir"], cwd=cwd)
    return code == 0


def git_status(cwd: Path | str | None = None) -> str:
    code, out, err = _run_git(["status", "--short", "--branch"], cwd=cwd)
    if code != 0:
        return err or "git status unavailable"
    return out.strip()


def changed_files(cwd: Path | str | None = None) -> list[str]:
    code, out, _ = _run_git(["status", "--short"], cwd=cwd)
    if code != 0:
        return []
    files: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # Status lines are "XY filename" or "XY filename -> filename"
        parts = line.split(" -> ")
        if len(parts) == 2:
            files.append(parts[1].strip())
        else:
            files.append(line[2:].strip())
    return files
