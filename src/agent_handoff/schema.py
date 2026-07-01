"""Provider-neutral handoff schema models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

PROVIDERS = {"codex", "claude-code", "kimi-code"}


class TaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    ABANDONED = "abandoned"


class Provider(str, Enum):
    CODEX = "codex"
    CLAUDE_CODE = "claude-code"
    KIMI_CODE = "kimi-code"
    UNKNOWN = "unknown"


def parse_provider(value: str | Provider | None) -> Provider:
    """Parse provider names defensively for CLI/user input."""
    if isinstance(value, Provider):
        return value
    if not value:
        return Provider.UNKNOWN
    normalized = str(value).strip().lower()
    aliases = {
        "claude": "claude-code",
        "claude_code": "claude-code",
        "claudecode": "claude-code",
        "kimi": "kimi-code",
        "kimi_code": "kimi-code",
        "kimicode": "kimi-code",
        "generic": "unknown",
        "any": "unknown",
    }
    normalized = aliases.get(normalized, normalized)
    try:
        return Provider(normalized)
    except ValueError:
        return Provider.UNKNOWN


class CapabilityType(str, Enum):
    PLUGIN = "plugin"
    MCP = "mcp"
    APP = "app"
    SHELL = "shell"
    FILESYSTEM = "filesystem"
    BROWSER = "browser"
    MANUAL = "manual"


class FallbackType(str, Enum):
    CAPTURED_RESULT = "captured-result"
    MANUAL_USER_INPUT = "manual-user-input"
    SWITCH_PROVIDER = "switch-provider"
    LOCAL_EQUIVALENT = "local-equivalent"
    SKIP_SAFE = "skip-safe"
    BLOCKED = "blocked"


class CommandResult(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"


class TestResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class CapabilityFallback(BaseModel):
    type: FallbackType = FallbackType.BLOCKED
    details: str = ""


class CapabilityEntry(BaseModel):
    provider: Provider
    type: CapabilityType
    id: str
    purpose: str = ""
    outputs_captured: bool = False
    required_to_continue: bool = False
    fallback: CapabilityFallback = Field(default_factory=CapabilityFallback)


class CommandRecord(BaseModel):
    command: str
    purpose: str | None = None
    result: CommandResult = CommandResult.UNKNOWN
    notes: str | None = None


class TestRecord(BaseModel):
    command: str
    result: TestResult = TestResult.UNKNOWN
    summary: str | None = None


class TaskBlock(BaseModel):
    title: str
    objective: str = ""
    status: TaskStatus = TaskStatus.IN_PROGRESS


class ProvidersBlock(BaseModel):
    created_by: Provider = Provider.UNKNOWN
    last_updated_by: Provider = Provider.UNKNOWN
    compatible_with: list[Provider] = Field(default_factory=list)

    @field_validator("compatible_with", mode="before")
    @classmethod
    def _normalize_compatible(cls, value: Any) -> list[Provider]:
        if value is None:
            return []
        return [parse_provider(v) for v in value]


class ContextBlock(BaseModel):
    repo_root: str | None = None
    workspace_roots: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ProgressBlock(BaseModel):
    done: list[str] = Field(default_factory=list)
    current: list[str] = Field(default_factory=list)
    next: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class WorkspaceBlock(BaseModel):
    git_status: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    commands_run: list[CommandRecord] = Field(default_factory=list)
    tests_run: list[TestRecord] = Field(default_factory=list)


class CapabilitiesBlock(BaseModel):
    used: list[CapabilityEntry] = Field(default_factory=list)
    required_next: list[CapabilityEntry] = Field(default_factory=list)
    missing_at_capture: list[CapabilityEntry] = Field(default_factory=list)
    fallbacks: list[CapabilityFallback] = Field(default_factory=list)


class SafetyBlock(BaseModel):
    secrets_touched: bool = False
    sensitive_sources: list[str] = Field(default_factory=list)
    destructive_actions: list[str] = Field(default_factory=list)
    needs_user_approval: list[str] = Field(default_factory=list)
    privacy_notes: list[str] = Field(default_factory=list)


class ResumeBlock(BaseModel):
    summary: str = ""
    recommended_next_provider: Provider = Provider.UNKNOWN
    next_prompt: str = ""


class RecallBlock(BaseModel):
    linked_memory_ids: list[str] = Field(default_factory=list)
    sync_status: Literal["not_configured", "synced", "failed"] = "not_configured"


class HandoffSchema(BaseModel):
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    handoff_id: str = Field(default_factory=lambda: _new_handoff_id(), alias="handoffId")
    created_at: datetime = Field(default_factory=lambda: _utc_now(), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: _utc_now(), alias="updatedAt")
    task: TaskBlock = Field(default_factory=TaskBlock)
    providers: ProvidersBlock = Field(default_factory=ProvidersBlock)
    context: ContextBlock = Field(default_factory=ContextBlock)
    progress: ProgressBlock = Field(default_factory=ProgressBlock)
    workspace: WorkspaceBlock = Field(default_factory=WorkspaceBlock)
    capabilities: CapabilitiesBlock = Field(default_factory=CapabilitiesBlock)
    safety: SafetyBlock = Field(default_factory=SafetyBlock)
    resume: ResumeBlock = Field(default_factory=ResumeBlock)
    recall: RecallBlock = Field(default_factory=RecallBlock)

    model_config = {"populate_by_name": True, "extra": "allow"}

    def bump_updated_at(self) -> None:
        self.updated_at = _utc_now()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_handoff_id() -> str:
    return _utc_now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
