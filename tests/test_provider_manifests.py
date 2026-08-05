"""Tests for provider plugin manifest validity."""

import json
import re
from pathlib import Path

from agent_handoff import __version__


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
    assert data["mcpServers"] == "./.codex-mcp.json"


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


def test_runtime_version_matches_project_and_provider_manifests() -> None:
    root = Path(__file__).parent.parent
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"$', project, re.MULTILINE)
    assert match is not None

    expected = match.group(1)
    assert __version__ == expected
    assert all(
        _load_manifest(path)["version"] == expected
        for path in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json", "kimi.plugin.json")
    )


def test_codex_mcp_manifest_uses_codex_shape() -> None:
    data = _load_manifest(".codex-mcp.json")
    assert "agent-handoff" in data
    assert "mcpServers" not in data
    assert data["agent-handoff"]["command"] == "uv"


def test_claude_mcp_manifest_uses_plugin_root() -> None:
    data = _load_manifest(".mcp.json")
    server = data["mcpServers"]["agent-handoff"]
    assert "${CLAUDE_PLUGIN_ROOT}" in server["args"]
    assert "cwd" not in server
