"""Tests for provider plugin manifest validity."""

import json
from pathlib import Path

import pytest


def _load_manifest(name: str) -> dict:
    path = Path(__file__).parent.parent / name
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_codex_manifest_valid() -> None:
    data = _load_manifest(".codex-plugin/plugin.json")
    assert data["name"] == "agent-handoff"
    assert data["skills"] == "./skills/"
    assert data["commands"] == "./commands/"
    assert data["interface"]["displayName"] == "Agent Handoff"
    assert data["mcpServers"] == "./.mcp.json"


def test_claude_manifest_valid() -> None:
    data = _load_manifest(".claude-plugin/plugin.json")
    assert data["name"] == "agent-handoff"
    assert data["skills"] == "./skills"
    assert data["commands"] == "./commands"
    assert data["mcpServers"] == "./.mcp.json"
    # Claude Code auto-discovers the default agents/ directory; declaring
    # agents explicitly currently fails `claude plugin validate`.
    assert "agents" not in data
    assert "interface" not in data


def test_kimi_manifest_valid() -> None:
    data = _load_manifest("kimi.plugin.json")
    assert data["name"] == "agent-handoff"
    assert "skills" in data
    assert data["commands"] == "./commands/"
    assert data["sessionStart"]["skill"] == "agent-handoff"
    assert "mcpServers" in data
    assert "agent-handoff" in data["mcpServers"]
    # Kimi Code plugin manifest ignores unsupported runtime fields such as
    # `tools`, `apps`, `inject`, and `configFile`.
    assert "tools" not in data
    assert "apps" not in data
    assert "inject" not in data
    assert "configFile" not in data


def test_all_manifests_share_id_and_version() -> None:
    codex = _load_manifest(".codex-plugin/plugin.json")
    claude = _load_manifest(".claude-plugin/plugin.json")
    kimi = _load_manifest("kimi.plugin.json")
    assert codex["name"] == claude["name"] == kimi["name"]
    assert codex["version"] == claude["version"] == kimi["version"]
