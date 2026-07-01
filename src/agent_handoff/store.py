"""Persistence layer for handoff artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schema import HandoffSchema, TaskStatus

DEFAULT_HANDOFF_DIR = ".handoff"
ACTIVE_JSON = "active.json"
ACTIVE_MD = "active.md"
HISTORY_DIR = "history"
EXPORTS_DIR = "exports"
ATTACHMENTS_DIR = "attachments"


def get_handoff_dir(repo_root: Path | str | None = None) -> Path:
    root = Path(repo_root) if repo_root else Path.cwd()
    return root / DEFAULT_HANDOFF_DIR


def ensure_handoff_dirs(handoff_dir: Path) -> None:
    handoff_dir.mkdir(parents=True, exist_ok=True)
    (handoff_dir / HISTORY_DIR).mkdir(exist_ok=True)
    (handoff_dir / EXPORTS_DIR).mkdir(exist_ok=True)
    (handoff_dir / ATTACHMENTS_DIR / "diffs").mkdir(parents=True, exist_ok=True)


def active_json_path(handoff_dir: Path) -> Path:
    return handoff_dir / ACTIVE_JSON


def active_md_path(handoff_dir: Path) -> Path:
    return handoff_dir / ACTIVE_MD


def exists(handoff_dir: Path | None = None) -> bool:
    hd = handoff_dir or get_handoff_dir()
    return active_json_path(hd).is_file()


def load(handoff_dir: Path | None = None) -> HandoffSchema:
    hd = handoff_dir or get_handoff_dir()
    path = active_json_path(hd)
    if not path.is_file():
        raise FileNotFoundError(f"No active handoff at {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return HandoffSchema.model_validate(data)


def save(handoff: HandoffSchema, handoff_dir: Path | None = None) -> Path:
    hd = handoff_dir or get_handoff_dir()
    ensure_handoff_dirs(hd)
    path = active_json_path(hd)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(handoff.model_dump(by_alias=True, mode="json"), fh, indent=2)
        fh.write("\n")
    return path


def snapshot(
    handoff: HandoffSchema,
    handoff_dir: Path | None = None,
    markdown: str | None = None,
) -> Path:
    hd = handoff_dir or get_handoff_dir()
    ensure_handoff_dirs(hd)
    timestamp = handoff.updated_at.strftime("%Y-%m-%dT%H%M%SZ")
    provider = handoff.providers.last_updated_by.value
    name = f"{timestamp}-{provider}"
    snap_json = hd / HISTORY_DIR / f"{name}.json"
    snap_md = hd / HISTORY_DIR / f"{name}.md"
    with snap_json.open("w", encoding="utf-8") as fh:
        json.dump(handoff.model_dump(by_alias=True, mode="json"), fh, indent=2)
        fh.write("\n")
    if markdown is not None:
        with snap_md.open("w", encoding="utf-8") as fh:
            fh.write(markdown)
            if not markdown.endswith("\n"):
                fh.write("\n")
    return snap_json


def write_active_md(content: str, handoff_dir: Path | None = None) -> Path:
    hd = handoff_dir or get_handoff_dir()
    ensure_handoff_dirs(hd)
    path = active_md_path(hd)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(content)
        if not content.endswith("\n"):
            fh.write("\n")
    return path


def close(handoff: HandoffSchema, handoff_dir: Path | None = None) -> Path:
    from .render import render_active

    hd = handoff_dir or get_handoff_dir()
    ensure_handoff_dirs(hd)
    handoff.task.status = TaskStatus.COMPLETE
    handoff.bump_updated_at()
    snap = snapshot(handoff, hd, render_active(handoff))
    # Clear active files after archiving.
    active_json = active_json_path(hd)
    active_md = active_md_path(hd)
    if active_json.is_file():
        active_json.unlink()
    if active_md.is_file():
        active_md.unlink()
    return snap


def validate_raw(data: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        HandoffSchema.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []))
            errors.append(f"{loc}: {err['msg']}")
        return False, errors
    return True, errors
