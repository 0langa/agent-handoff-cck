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
    assert data["id"] == "agent-handoff"
    assert "skills" in data
    assert "commands" in data


def test_claude_manifest_valid() -> None:
    data = _load_manifest(".claude-plugin/plugin.json")
    assert data["id"] == "agent-handoff"
    assert "commands" in data
    assert "agents" in data


def test_kimi_manifest_valid() -> None:
    data = _load_manifest("kimi.plugin.json")
    assert data["id"] == "agent-handoff"
    assert "commands" in data
    assert "skills" in data


def test_all_manifests_share_id_and_version() -> None:
    codex = _load_manifest(".codex-plugin/plugin.json")
    claude = _load_manifest(".claude-plugin/plugin.json")
    kimi = _load_manifest("kimi.plugin.json")
    assert codex["id"] == claude["id"] == kimi["id"]
    assert codex["version"] == claude["version"] == kimi["version"]
