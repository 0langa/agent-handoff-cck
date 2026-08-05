"""Export provider-specific continuation prompts."""

from __future__ import annotations

from pathlib import Path

from .render import render_export
from .schema import HandoffSchema, Provider, parse_provider
from .store import EXPORTS_DIR


def export_path(handoff_dir: Path, target: Provider) -> Path:
    return handoff_dir / EXPORTS_DIR / f"{target.value}.md"


def export_to(
    handoff: HandoffSchema,
    target: str,
    handoff_dir: Path | None = None,
) -> Path:
    from .store import ensure_handoff_dirs, get_handoff_dir

    hd = handoff_dir or get_handoff_dir()
    ensure_handoff_dirs(hd)

    provider = parse_provider(target)
    content = render_export(handoff, provider)
    path = export_path(hd, provider)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(content)
        if not content.endswith("\n"):
            fh.write("\n")
    return path
