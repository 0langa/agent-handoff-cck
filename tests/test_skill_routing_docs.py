"""Tests for skill auto-activation and command MCP preference."""

from pathlib import Path

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "agent-handoff" / "SKILL.md"
COMMANDS_DIR = Path(__file__).parent.parent / "commands"


@pytest.fixture
def skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_mentions_mcp_tools(skill_text: str) -> None:
    assert "handoff_init" in skill_text
    assert "handoff_capture" in skill_text
    assert "handoff_verify" in skill_text
    assert "handoff_export" in skill_text
    assert "handoff_resume" in skill_text


def test_skill_has_trigger_words(skill_text: str) -> None:
    lower = skill_text.lower()
    for word in [
        "kimi",
        "claude",
        "codex",
        "new chat",
        "handoff",
        "checkpoint",
        "resume",
        "verify",
        "export",
        "transfer",
        "continue",
        "switch agents",
    ]:
        assert word in lower, f"missing trigger word: {word}"


def test_skill_prefers_mcp_over_cli(skill_text: str) -> None:
    assert "Prefer the Agent Handoff **MCP tools**" in skill_text
    assert "Do not tell the user to run CLI commands" in skill_text


def test_skill_requires_explicit_repo_root(skill_text: str) -> None:
    assert "Always pass `repo_root` explicitly" in skill_text
    assert "not the plugin installation directory" in skill_text


def test_commands_prefer_mcp() -> None:
    for path in COMMANDS_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "## Chat-native behavior" in text, f"{path.name} missing chat-native section"
        assert "MCP" in text, f"{path.name} does not mention MCP"
        assert "Always pass `repo_root` explicitly" in text, (
            f"{path.name} does not require explicit repo_root"
        )
