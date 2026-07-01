"""Capability model and provider capability matrix."""

from __future__ import annotations

from .schema import (
    CapabilityEntry,
    CapabilityType,
    FallbackType,
    Provider,
)

# Minimal static capability matrix for MVP.
# Each capability maps to providers that are known to support it.
CAPABILITY_MATRIX: dict[str, set[Provider]] = {
    "gmail@openai-curated-remote": {Provider.CODEX},
    "github@openai-curated-remote": {Provider.CODEX},
    "webde-connector": {Provider.CODEX},
    "bash": {Provider.CLAUDE_CODE, Provider.KIMI_CODE},
    "git": {Provider.CODEX, Provider.CLAUDE_CODE, Provider.KIMI_CODE},
    "file-read": {Provider.CODEX, Provider.CLAUDE_CODE, Provider.KIMI_CODE},
    "file-edit": {Provider.CODEX, Provider.CLAUDE_CODE, Provider.KIMI_CODE},
}


def supported_by(capability_id: str, provider: Provider) -> bool:
    providers = CAPABILITY_MATRIX.get(capability_id)
    if providers is None:
        return True  # Unknown capability; assume portable unless told otherwise.
    return provider in providers


def check_missing_capabilities(
    handoff_caps: list[CapabilityEntry],
    current_provider: Provider,
) -> list[CapabilityEntry]:
    missing: list[CapabilityEntry] = []
    for cap in handoff_caps:
        if cap.required_to_continue and not supported_by(cap.id, current_provider):
            missing.append(cap)
    return missing


def make_capability(
    provider: Provider,
    type: CapabilityType,
    id: str,
    purpose: str,
    outputs_captured: bool,
    required_to_continue: bool,
    fallback_type: FallbackType,
    fallback_details: str,
) -> CapabilityEntry:
    return CapabilityEntry(
        provider=provider,
        type=type,
        id=id,
        purpose=purpose,
        outputs_captured=outputs_captured,
        required_to_continue=required_to_continue,
        fallback={"type": fallback_type, "details": fallback_details},
    )
