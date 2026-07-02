"""Tests for provider alias normalization."""

import pytest

from agent_handoff.schema import Provider, detect_provider, normalize_provider, parse_provider


def test_parse_provider_aliases() -> None:
    assert parse_provider("kimi") == Provider.KIMI_CODE
    assert parse_provider("kimi code") == Provider.KIMI_CODE
    assert parse_provider("claude") == Provider.CLAUDE_CODE
    assert parse_provider("claude code") == Provider.CLAUDE_CODE
    assert parse_provider("openai codex") == Provider.CODEX
    assert parse_provider("generic") == Provider.UNKNOWN
    assert parse_provider("not-a-provider") == Provider.UNKNOWN


def test_normalize_provider_valid_values() -> None:
    assert normalize_provider("codex") == Provider.CODEX
    assert normalize_provider("kimi-code") == Provider.KIMI_CODE
    assert normalize_provider("claude-code") == Provider.CLAUDE_CODE
    assert normalize_provider("generic") == Provider.UNKNOWN


def test_normalize_provider_current_aliases() -> None:
    assert normalize_provider("same", current="codex") == Provider.CODEX
    assert normalize_provider("same-provider", current="kimi-code") == Provider.KIMI_CODE
    assert normalize_provider("new chat", current="claude-code") == Provider.CLAUDE_CODE


def test_normalize_provider_invalid_raises() -> None:
    with pytest.raises(ValueError):
        normalize_provider("not-a-provider")


def test_detect_provider_default_unknown() -> None:
    # No provider env vars are set in the test environment.
    assert detect_provider() == Provider.UNKNOWN
