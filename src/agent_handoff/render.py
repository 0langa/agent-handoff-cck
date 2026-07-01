"""Render handoff schema to Markdown."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape

from .schema import HandoffSchema, Provider


def _get_env() -> Environment:
    template_dir = Path(__file__).parent.parent.parent / "templates"
    if template_dir.is_dir():
        loader: FileSystemLoader | PackageLoader = FileSystemLoader(str(template_dir))
    else:
        loader = PackageLoader("agent_handoff", "templates")
    return Environment(
        loader=loader,
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_active(handoff: HandoffSchema) -> str:
    env = _get_env()
    template = env.get_template("active.md.j2")
    return template.render(h=handoff)


def render_export(handoff: HandoffSchema, target: Provider) -> str:
    env = _get_env()
    template_name = {
        Provider.CODEX: "export-codex.md.j2",
        Provider.CLAUDE_CODE: "export-claude-code.md.j2",
        Provider.KIMI_CODE: "export-kimi-code.md.j2",
    }.get(target, "export-generic.md.j2")
    template = env.get_template(template_name)
    return template.render(h=handoff, target=target)
