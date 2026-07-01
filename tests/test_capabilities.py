"""Tests for capability model."""

import pytest

from agent_handoff.capabilities import (
    CAPABILITY_MATRIX,
    check_missing_capabilities,
    make_capability,
    supported_by,
)
from agent_handoff.schema import CapabilityType, FallbackType, Provider


def test_gmail_only_on_codex() -> None:
    assert supported_by("gmail@openai-curated-remote", Provider.CODEX)
    assert not supported_by("gmail@openai-curated-remote", Provider.CLAUDE_CODE)
    assert not supported_by("gmail@openai-curated-remote", Provider.KIMI_CODE)


def test_unknown_capability_assumed_portable() -> None:
    assert supported_by("some-unknown-tool", Provider.KIMI_CODE)


def test_check_missing_capabilities_detects_gap() -> None:
    cap = make_capability(
        provider=Provider.CODEX,
        type=CapabilityType.PLUGIN,
        id="gmail@openai-curated-remote",
        purpose="read email",
        outputs_captured=False,
        required_to_continue=True,
        fallback_type=FallbackType.SWITCH_PROVIDER,
        fallback_details="use Codex",
    )
    missing = check_missing_capabilities([cap], Provider.CLAUDE_CODE)
    assert len(missing) == 1
    assert missing[0].id == "gmail@openai-curated-remote"


def test_check_missing_capabilities_ignores_non_required() -> None:
    cap = make_capability(
        provider=Provider.CODEX,
        type=CapabilityType.PLUGIN,
        id="gmail@openai-curated-remote",
        purpose="read email",
        outputs_captured=False,
        required_to_continue=False,
        fallback_type=FallbackType.SWITCH_PROVIDER,
        fallback_details="use Codex",
    )
    missing = check_missing_capabilities([cap], Provider.CLAUDE_CODE)
    assert not missing
