"""Tests for handoff schema models."""

import json
from pathlib import Path

import pytest

from agent_handoff.schema import (
    CapabilityEntry,
    CapabilityFallback,
    CapabilityType,
    FallbackType,
    HandoffSchema,
    Provider,
    TaskStatus,
)


def test_default_handoff() -> None:
    h = HandoffSchema(task={"title": "test"})
    assert h.schema_version == "1.0"
    assert h.task.title == "test"
    assert h.task.status == TaskStatus.IN_PROGRESS
    assert h.providers.created_by == Provider.UNKNOWN


def test_handoff_roundtrip() -> None:
    h = HandoffSchema(
        task={"title": "t", "objective": "o", "status": TaskStatus.BLOCKED.value},
        providers={
            "created_by": "codex",
            "last_updated_by": "claude-code",
            "compatible_with": ["codex", "claude-code", "kimi-code"],
        },
        progress={"done": ["a"], "next": ["b"]},
    )
    data = h.model_dump(by_alias=True, mode="json")
    h2 = HandoffSchema.model_validate(data)
    assert h2.task.title == "t"
    assert h2.providers.created_by == Provider.CODEX
    assert h2.progress.done == ["a"]


def test_provider_enum_from_string() -> None:
    h = HandoffSchema(task={"title": "t"}, providers={"created_by": "kimi-code"})
    assert h.providers.created_by == Provider.KIMI_CODE


def test_capability_entry() -> None:
    cap = CapabilityEntry(
        provider=Provider.CODEX,
        type=CapabilityType.PLUGIN,
        id="gmail@openai-curated-remote",
        purpose="search inbox",
        outputs_captured=True,
        fallback=CapabilityFallback(
            type=FallbackType.SWITCH_PROVIDER,
            details="switch to Codex",
        ),
    )
    assert cap.fallback.type == FallbackType.SWITCH_PROVIDER


def test_json_schema_file_matches_model(tmp_path: Path) -> None:
    schema_path = Path(__file__).parent.parent / "schemas" / "handoff.schema.json"
    assert schema_path.is_file()
    with schema_path.open("r", encoding="utf-8") as fh:
        file_schema = json.load(fh)
    model_schema = HandoffSchema.model_json_schema(by_alias=True)
    assert file_schema["title"] == model_schema["title"]
    assert "task" in file_schema["properties"]
    assert "capabilities" in file_schema["properties"]
